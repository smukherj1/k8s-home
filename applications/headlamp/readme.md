# Authentik Integration for Login

1. Create a OIDC Provider on Authentik.

1. Create the secrets for headlamp

```shell

# Get the client id, secret and Open ID config issuer URLs from the
# Authentik OIDC Provider created for headlamp.

CLIENT_ID=""
CLIENT_SECRET=""
ISSUER_URL=""
kubectl -n headlamp create secret generic \
    headlamp-oidc-secrets \
    --from-literal=OIDC_CLIENT_ID=${CLIENT_ID} \
    --from-literal=OIDC_CLIENT_SECRET=${CLIENT_SECRET} \
    --from-literal=OIDC_ISSUER_URL=${ISSUER_URL} \
    --from-literal=OIDC_SCOPES="openid profile email"
```
