Setup instructions [link](https://docs.goauthentik.io/install-config/install/kubernetes/)
Secrets in Authentik Helm values [link](https://github.com/goauthentik/authentik/discussions/12852)

# Secret Generation

```shell
AUTHENTIK_SECRET_KEY=$(openssl rand 60 | base64 -w 0)
```
