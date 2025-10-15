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
