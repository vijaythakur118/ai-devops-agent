from kubernetes import client, config
from kubernetes.client.rest import ApiException
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _load_kube_config():
    if settings.k8s_in_cluster:
        config.load_incluster_config()
    elif settings.kubeconfig_path:
        config.load_kube_config(config_file=settings.kubeconfig_path)
    else:
        config.load_kube_config()


def deploy_service(service: str, image: str, namespace: str = "default", replicas: int = 1) -> dict:
    _load_kube_config()
    apps_v1 = client.AppsV1Api()

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=service, namespace=namespace),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels={"app": service}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": service}),
                spec=client.V1PodSpec(
                    containers=[client.V1Container(name=service, image=image)]
                ),
            ),
        ),
    )

    try:
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        return {"status": "created", "service": service, "image": image}
    except ApiException as e:
        if e.status == 409:
            apps_v1.patch_namespaced_deployment(name=service, namespace=namespace, body=deployment)
            return {"status": "updated", "service": service, "image": image}
        raise


def get_deployment_status(service: str, namespace: str = "default") -> dict:
    _load_kube_config()
    apps_v1 = client.AppsV1Api()
    try:
        dep = apps_v1.read_namespaced_deployment(name=service, namespace=namespace)
        return {
            "service": service,
            "desired": dep.spec.replicas,
            "ready": dep.status.ready_replicas or 0,
            "available": dep.status.available_replicas or 0,
        }
    except ApiException as e:
        return {"error": str(e), "service": service}


def restart_deployment(service: str, namespace: str = "default") -> dict:
    _load_kube_config()
    apps_v1 = client.AppsV1Api()
    from datetime import datetime, timezone
    patch = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(name=service, namespace=namespace, body=patch)
    return {"status": "restarted", "service": service}


def get_pod_logs(service: str, namespace: str = "default", tail: int = 100) -> dict:
    _load_kube_config()
    core_v1 = client.CoreV1Api()
    pods = core_v1.list_namespaced_pod(namespace=namespace, label_selector=f"app={service}")
    if not pods.items:
        return {"error": "No pods found", "service": service}
    pod_name = pods.items[0].metadata.name
    logs = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail)
    return {"pod": pod_name, "logs": logs}


def rollback_deployment(service: str, namespace: str = "default") -> dict:
    _load_kube_config()
    apps_v1 = client.AppsV1Api()
    # Trigger rollback via annotation patch (kubectl rollout undo equivalent)
    patch = {"spec": {"rollbackTo": {"revision": 0}}}
    try:
        apps_v1.patch_namespaced_deployment(name=service, namespace=namespace, body=patch)
        return {"status": "rolled_back", "service": service}
    except ApiException as e:
        return {"error": str(e), "service": service}
