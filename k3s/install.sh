#!/usr/bin/bash

set -eu

curl -sfL https://get.k3s.io | K3S_KUBECONFIG_MODE="644" sh - --disable=traefik --disable=metrics-server --disable=servicelb

# Uninstalling
# /usr/local/bin/k3s-killall.sh
# /usr/local/bin/k3s-uninstall.sh

# Alternative sudoless kubectl
# export KUBECONFIG="/home/suvanjan/.kube/config"
# cat /etc/rancher/k3s/k3s.yaml > /home/suvanjan/.kube/config