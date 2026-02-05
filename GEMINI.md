

This repository contains the Kubernetes manifests for the applications running on the k3s kubernetes cluster
on my home lab.

## MCP Servers

The Github and Helm MCP servers are avaiable to query the latest helm chart versions and use these to
update the kubernetes manifests running in the cluster.

The kubernetes manifests are located in the `applications` directory and are stored in the Github repositry
github.com:smukherj1/k8s-home. The manifests are applied to the cluster using ArgoCD.

# Application Kubernetes Manifests

The application kubernetes manifests are located in the `applications` directory. The YAML files directly under
this directory are the manifests for the ArgoCD applications.

Under the `applications` directory, there are subdirectories for each application with the same name as the
application manifest (without the .yml extension).

# Updating Applications

When asked to update applications, query the latest helm chart version using the helm mcp server. Then create
a single pull request to update the helm chart version in the `applications` directory.

In the pull request, use the following format for the title:
Updating helm chart versions.

In the body of the pull request, use the following format for each application:
<application-name>: update from <old-version> to <new-version>



