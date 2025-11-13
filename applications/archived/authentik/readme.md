Setup instructions [link](https://docs.goauthentik.io/install-config/install/kubernetes/)
Secrets in Authentik Helm values [link](https://github.com/goauthentik/authentik/discussions/12852)
Envrironment variables [link](https://docs.goauthentik.io/install-config/configuration/#set-your-environment-variables)

# Secret Generation

```shell
AUTHENTIK_SECRET_KEY=$(openssl rand 60 | base64 -w 0)

kubectl -n authentik create secret generic authentik-secrets --from-literal=secret-key=${AUTHENTIK_SECRET_KEY}
```

# Cloudflare Tunnel Setup

```shell
CLOUDFLARE_TUNNEL_TOKEN=""

kubectl -n authentik create secret generic cloudflare-tunnel-secrets --from-literal=token=${CLOUDFLARE_TUNNEL_TOKEN}
```
