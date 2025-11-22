# Deploy the Expenses Server

The expenses server is Web App whose source code is available at
https://github.com/smukherj1/expenses-v2.

The server is built into a Docker image on GitHub Container Registry
as ghcr.io/smukherj1/expenses-v2.

# Better Auth Secret Creation

```shell
KEYCLOAK_CLIENT_SECRET=""
BETTER_AUTH_SECRET=$(openssl rand -base64 32)
kubectl -n expenses create secret generic expenses-secrets --from-literal=better-auth-secret=${BETTER_AUTH_SECRET} --from-literal=keycloak-client-secret=${KEYCLOAK_CLIENT_SECRET}
```