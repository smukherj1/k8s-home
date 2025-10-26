Immich Setup instructions [here](https://github.com/immich-app/immich-charts/blob/main/README.md).

# Initialize Postgres Secret

1. Print the cnpg cluster DB URL

```shell
$ kubectl get secret immich-db-cluster-app -n cnpg -o json | jq -r '.data."fqdn-uri"' | base64 -d
```

1. Create a copy of this secret in the immich namespace to make it accessible by the
   immich server

```shell
kubectl create secret generic db-url -n immich --from-literal=DB_URL=[value from above]
```

# Testing Immich Server with Port Forwarning

```shell
kubectl -n immich port-forward svc/immich-server 8080:2283

ssh -L 8080:localhost:8080 suvanjan@[node ip]
```
