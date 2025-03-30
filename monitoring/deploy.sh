#!/usr/bin/bash

set -eu

# https://grafana.com/docs/grafana/latest/setup-grafana/installation/helm/
# https://grafana.com/docs/loki/latest/setup/install/helm/install-monolithic/
# helm repo add grafana https://grafana.github.io/helm-charts
# helm repo update

# Function to handle component commands
handle_component_command() {
  local component="$1"
  local command="$2"

  echo "Running action ${command} for ${component}"

  case "$command" in
    "install")
        helm repo update
        helm install ${component} grafana/${component} -n grafana -f ${component}_values.yml > ${component}_deployment.log
      ;;
    "update")
        helm upgrade ${component} grafana/${component} -f ${component}_values.yml -n grafana > ${component}_deployment.log
      ;;
    "uninstall")
        helm uinstall ${component}
      ;;
    *)
      echo "Invalid command: $component"
      return 1
      ;;
  esac
  return 0
}

# Check if two arguments are provided
if [ $# -ne 2 ]; then
  echo "Usage: $0 <component> <command>"
  echo "  component: grafana, loki, alloy"
  echo "  command: install, update, uninstall"
  exit 1
fi

# Call the function with the arguments
handle_component_command "$1" "$2"

exit $? # Exit with the return code of the function