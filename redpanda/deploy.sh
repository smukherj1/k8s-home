#!/usr/bin/bash

set -eu

# https://docs.redpanda.com/current/deploy/deployment-option/self-hosted/kubernetes/local-guide/

handle_command() {
  local command="$1"

  echo "Running command ${command}"

  case "$command" in
    "bootstrap")
        helm repo add jetstack https://charts.jetstack.io
        helm repo add redpanda https://charts.redpanda.com/
      ;;
    "install")
        helm repo update
        helm install cert-manager jetstack/cert-manager \
          --set crds.enabled=true \
          --namespace cert-manager  \
          --create-namespace > cert-manager_deployment.log
        
        helm install redpanda redpanda/redpanda \
          --version 5.9.21 \
          --namespace redpanda \
          --create-namespace \
          -f redpanda_values.yaml > redpanda_deployment.log
      ;;
    "update")
        helm upgrade redpanda redpanda/redpanda -f redpanda_values.yml -n redpanda > redpanda_deployment.log
      ;;
    "uninstall")
        helm uinstall redpanda
        helm uinstall cert-manager
      ;;
    *)
      echo "Invalid command: $component"
      return 1
      ;;
  esac
  return 0
}

# Check if two arguments are provided
if [ $# -ne 1 ]; then
  echo "Usage: $0 <command>"
  echo "  command: bootstrap, install, update, uninstall"
  exit 1
fi

handle_command "$1"

exit $? # Exit with the return code of the function