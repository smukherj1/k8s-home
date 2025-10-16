# Bootstrapping a Ubuntu Server as a Kubernetes Node

## Step 1: K3S Installation

```shell
curl -sfL https://get.k3s.io | K3S_KUBECONFIG_MODE="644" sh -s - --disable=traefik --disable=metrics-server --disable=servicelb
```

## Step 2: Enable Graceful Pod Termination on Node Shutdown

Reference [link](https://github.com/k3s-io/k3s/discussions/4319)

1. Create a directory and empty kubelet config file.

```shell
mkdir ~/.k3s && touch ~/.k3s/kubelet.config
```

1. Then add the following to the `~/.k3s/kubelet.config`

```YAML
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
shutdownGracePeriod: 15s
shutdownGracePeriodCriticalPods: 10s
```

1. Edit the systemd config file k3s at `/etc/systemd/system/k3s.service`

```
...
ExecStart=/usr/local/bin/k3s \
    server \
        '--disable=traefik' \
        '--disable=metrics-server' \
        '--disable=servicelb' \
        --kubelet-arg config=/home/<username>/.k3s/kubelet.config \
```

1. Then restart the service and confirm the k3s server is running.

```shell
sudo systemctl daemon-reload
sudo systemctl restart k3s
sudo systemctl status k3s
```

## Step 5: Install Helm

1. Verify the contents of `https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3`.

1. Download and install Helm

```shell
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## Step 4: Install Tailscale VPN Client and Ingress Controller

1. Install the tailscale client where you'll be accessing services running on
   the k8s cluster from. [link](https://tailscale.com/kb/1031/install-linux).

1. Following the [prerequisites](https://tailscale.com/kb/1236/kubernetes-operator#prerequisites),
   add a `JSON` file to a Github repo with the following contents:

```JSON
{
  "tagOwners": {
    "tag:k8s-operator": [],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

Then go to Settings in the Tailscale console and link to the submitted JSON file in the
tailnet policy settings.

1. Install the tailscale Ingress Controller [link](https://tailscale.com/kb/1439/kubernetes-operator-cluster-ingress).

```shell
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update
KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade \
  --install \
  tailscale-operator \
  tailscale/tailscale-operator \
  --namespace=tailscale \
  --create-namespace \
  --set-string oauth.clientId="<OAauth client ID>" \
  --set-string oauth.clientSecret="<OAuth client secret>" \
  --wait
```

The output should look something like

```shell
Release "tailscale-operator" does not exist. Installing it now.
NAME: tailscale-operator
LAST DEPLOYED: Thu Oct 16 21:58:28 2025
NAMESPACE: tailscale
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
You have successfully installed the Tailscale Kubernetes Operator!

Once connected, the operator should appear as a device within the Tailscale admin console:
https://login.tailscale.com/admin/machines

If you have not used the Tailscale operator before, here are some examples to try out:

* Private Kubernetes API access and authorization using the API server proxy
  https://tailscale.com/kb/1437/kubernetes-operator-api-server-proxy

* Private access to cluster Services using an ingress proxy
  https://tailscale.com/kb/1439/kubernetes-operator-cluster-ingress

* Private access to the cluster's available subnets using a subnet router
  https://tailscale.com/kb/1441/kubernetes-operator-connector

You can also explore the CRDs, operator, and associated resources within the tailscale namespace:

$ kubectl explain connector
$ kubectl explain proxygroup
$ kubectl explain proxyclass
$ kubectl explain recorder
$ kubectl explain dnsconfig

If you're interested to explore what resources were created:

$ kubectl --namespace=tailscale get all -l app.kubernetes.io/managed-by=Helm

```
