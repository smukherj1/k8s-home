https://www.keycloak.org/operator/basic-deployment

# Key Creator

TODO: Exploring switching to auto-rotated keys from Cert Manager

```shell
# Generate a 3 year certificate
openssl req -subj '/CN=keycloak.suvanjanlabs.com/O=Suvanjan Labs./C=CA' -newkey rsa:4096 -nodes -keyout key.pem -x509 -days 1095 -out certificate.pem

kubectl -n keycloak create secret tls keycloak-tls-secret --cert certificate.pem --key key.pem

rm certificate.pem key.pem
```
