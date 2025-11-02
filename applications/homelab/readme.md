# Workload Identity Federation

The homelab service account is connected to a Google Cloud Service Account.
Setup instructions: [link](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-kubernetes#kubernetes)

## Issuer

```shell
$ kubectl get --raw /.well-known/openid-configuration | jq -r .issuer
https://kubernetes.default.svc.cluster.local
```

## JwKS

```shell
$ kubectl get --raw /openid/v1/jwks
```

```JSON
{"keys":[{"use":"sig","kty":"RSA","kid":"fuNL37K14ZiodLEvvsnoNGimsNBID35sSwU309szO-0","alg":"RS256","n":"3nHvv39zdZ_APywOHsNe38wia5tFf7lWMwNngPCRxE7Dp0VnBx-p9mcuYXs-sIMmcOj_8dJQZlrYCkpk2nKey_Qf_E9KIWG_o3GROB1N9fHDDRYNwCz699Mbcy3Qrs10cSou41ORYZxdjO2E6pREJzM2hC9Go9-YP-rX9ccdgA1e8HhTK7QlvU7CMVc3bG5OfjJ2xxahbLuhoVC-qz62ktml5AqNvNKMvNkfyO6s-BJq2d5SnCGAB16hZQjzjoESSztCajtRCFtwCPxqlm_V1baUu3DmGctJsStfKCK1UMldtQ1r8V6JcqdGT5HrGIayNlt_fNkiJIjv96A7K3pV-w","e":"AQAB"}]}
```

Copy the default audience to the project volume in the Pod manifest that'll use the workload
identity.
