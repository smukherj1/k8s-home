# Creating Secret for Admin Console Username and Password

```shell
kubectl create namespace pihole
kubectl create secret generic admin-creds --from-literal=user=admin --from-literal=password=<password> -n pihole
```
