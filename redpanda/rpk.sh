#/usr/bin/bash

set -eu

rpk="kubectl --namespace redpanda exec -i -t redpanda-0 -c redpanda -- rpk"

${rpk} "$@"

