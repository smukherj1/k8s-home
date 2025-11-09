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
    --from-literal=clientID=${CLIENT_ID} \
    --from-literal=clientSecret=${CLIENT_SECRET} \
    --from-literal=issuerURL=${ISSUER_URL} \
    --from-literal=scopes="openid profile email"
```
