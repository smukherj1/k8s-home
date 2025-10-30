Cloud Native Postgres Database Cluster: [link](https://github.com/cloudnative-pg/charts)

Used by Immich.

# Backup

```shell
kubectl -n cnpg exec immich-db-cluster-1 -c postgres \
  -- pg_dumpall --clean --if-exists --username=postgres | gzip > immich-db-backup.gz
```
