# Upgrading the K3s Cluster

This document covers upgrading the K3s version on the home lab cluster. It assumes the node was installed using
the procedure in [bootstrap.md](bootstrap.md), with K3s managed by the `k3s` systemd service.

K3s official references:

- [K3s manual upgrades](https://docs.k3s.io/upgrades/manual)
- [K3s releases](https://github.com/k3s-io/k3s/releases)

## Before Upgrading

1. Pick the target K3s version from the [K3s releases](https://github.com/k3s-io/k3s/releases).

   Use a full K3s version string, for example:

   ```shell
   v1.33.1+k3s1
   ```

1. Do not skip Kubernetes minor versions.

   For example, upgrade from `v1.31.x+k3s1` to `v1.32.x+k3s1` before upgrading to `v1.33.x+k3s1`.

1. Check the current cluster and node version.

   ```shell
   kubectl get nodes -o wide
   k3s --version
   sudo systemctl status k3s
   ```

   Record the current K3s version before upgrading so there is an explicit rollback target.

1. Confirm the existing K3s service arguments.

   The K3s install script recreates the systemd service from the arguments passed to it. If an argument is omitted
   during upgrade, it can be removed from the service configuration.

   ```shell
   sudo systemctl cat k3s
   ```

   For this cluster, preserve the K3s install options from [Step 1: K3S Installation](bootstrap.md#step-1-k3s-installation)
   and the kubelet config argument from
   [Step 2: Enable Graceful Pod Termination on Node Shutdown](bootstrap.md#step-2-enable-graceful-pod-termination-on-node-shutdown).

1. Optional: cordon the node if you want to prevent new workloads from being scheduled during the upgrade.

   For a single-node cluster, do not drain the node unless you are prepared for the workloads to stop. Draining a
   single-node cluster can evict workloads that have nowhere else to run.

   ```shell
   kubectl cordon <node-name>
   ```

## Upgrade K3s

Run the installer again with the target version and the same K3s arguments used by the current service.

```shell
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION=<target-version> \
  K3S_KUBECONFIG_MODE="644" \
  sh -s - \
    --disable=traefik \
    --disable=metrics-server \
    --disable=servicelb \
    --kubelet-arg config=/home/suvanjan/.k3s/kubelet.config
```

Example:

```shell
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION=v1.33.1+k3s1 \
  K3S_KUBECONFIG_MODE="644" \
  sh -s - \
    --disable=traefik \
    --disable=metrics-server \
    --disable=servicelb \
    --kubelet-arg config=/home/suvanjan/.k3s/kubelet.config
```

The installer downloads the requested K3s binary, updates the systemd unit, and restarts `k3s`.

## Verify the Upgrade

1. Confirm the service restarted successfully.

   ```shell
   sudo systemctl status k3s
   sudo journalctl -u k3s -n 100 --no-pager
   ```

1. Confirm the binary and node versions.

   ```shell
   k3s --version
   kubectl get nodes -o wide
   kubectl version
   ```

1. Confirm core workloads recovered.

   ```shell
   kubectl get pods -A
   kubectl get applications -n argocd
   ```

1. If the node was cordoned before the upgrade, uncordon it.

   ```shell
   kubectl uncordon <node-name>
   ```

## After Upgrading

1. Confirm the graceful shutdown kubelet configuration is still referenced in the service.

   ```shell
   sudo systemctl cat k3s
   ```

   The service should still include:

   ```shell
   --kubelet-arg config=/home/suvanjan/.k3s/kubelet.config
   ```

   If this is missing, repeat the relevant service configuration from
   [Step 2: Enable Graceful Pod Termination on Node Shutdown](bootstrap.md#step-2-enable-graceful-pod-termination-on-node-shutdown).

1. Upgrade cluster add-ons separately when needed.

   - For the Tailscale operator, use
     [Step 4a: To Upgrade An Existing Tailscale Operator Installation](bootstrap.md#step-4a-to-upgrade-an-existing-tailscale-operator-installation).
   - For Argo CD, update both the install manifest URL and the matching reference in
     `applications/argocd/kustomization.yml` as described in
     [Step 5: Install Argo CD](bootstrap.md#step-5-install-argo-cd).
   - For application Helm charts managed by Argo CD, see
     [k8s-manifests.md](k8s-manifests.md#updating-helm-chart-versions).

## Roll Back

If the upgraded node is unhealthy, rerun the installer with the previous K3s version and the same service arguments.

```shell
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_VERSION=<previous-version> \
  K3S_KUBECONFIG_MODE="644" \
  sh -s - \
    --disable=traefik \
    --disable=metrics-server \
    --disable=servicelb \
    --kubelet-arg config=/home/suvanjan/.k3s/kubelet.config
```

Then verify the service and cluster state again using the commands in [Verify the Upgrade](#verify-the-upgrade).
