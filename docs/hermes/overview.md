# Hermes Agent Overview

[Hermes Agent](https://hermes-agent.nousresearch.com/docs/) is the AI agent that operates this home lab. It runs on
the Kubernetes node, but **not** as a Kubernetes workload: it is a host-level systemd **user** service that talks to
Discord, works in the `k8s-home` git checkout, and has `kubectl`, git, and shell access to the node.

This document is the entry point. The details are split across:

- [configuration.md](configuration.md) — `config.yaml` vs `.env`, model/provider, platforms, skills, plugins, GitHub auth.
- [operations.md](operations.md) — start/stop/restart, health checks, logs, upgrades, backups, troubleshooting.
- [rebuild.md](rebuild.md) — appendix: rebuild the whole setup from a bare Ubuntu install.

## Why Hermes Is Not in Kubernetes

Everything else in this repository is reconciled into the cluster by Argo CD. Hermes deliberately is not, for three
reasons:

1. **Recovery must not depend on what is being repaired.** Hermes is the thing that diagnoses the cluster, edits the
   manifests, and opens the pull request. Running it inside the cluster would make cluster or Argo CD breakage also
   break the tool used to fix it.
2. **It needs node-local context.** The agent works directly in `/home/suvanjan/depot/k8s-home`, reads
   `/etc/rancher/k3s/k3s.yaml`, and shells out to `kubectl`, `helm`, and `git`. Mounting the host kubeconfig and a
   writable repo checkout into a pod would be more privileged and less inspectable than a user service.
3. **Restart semantics.** An agent turn is a long-lived, stateful process (running tool calls, pending approvals). A
   pod restart, eviction, or node drain would cut it mid-turn; a systemd unit with `Restart=always` gives one
   predictable restart policy and a single place to look.

The trade-off: **Hermes is not declarative**. Its configuration is not in this repo and not reconciled by Argo CD.
Drift is possible, and everything it depends on is only as recoverable as the manual backup procedure in
[operations.md](operations.md#backup-and-restore).

## Runtime Inventory

Single profile (`default`), one gateway process, no cron jobs.

| Component | Location | Notes |
|---|---|---|
| Agent install | `~/.hermes/hermes-agent` | git checkout, ~1.1 GB, updated by `hermes update` |
| Hermes home | `~/.hermes` (`HERMES_HOME`) | all state below |
| Settings | `~/.hermes/config.yaml` | plain YAML, edited with `hermes config set` |
| Secrets | `~/.hermes/.env` | tokens and keys only |
| Session history | `~/.hermes/state.db` | SQLite + FTS5 (~5 MB) |
| Logs | `~/.hermes/logs/` | `gateway.log`, `agent.log`, `errors.log` |
| Skills | `~/.hermes/skills/` | ~45 skills in 13 categories |
| Plugins | `~/.hermes/plugins/` | `github_app` |
| Git credential helper | `~/.hermes/bin/git-credential-github-app.py` | mints short-lived App tokens |
| Service unit | `~/.config/systemd/user/hermes-gateway.service` | `Restart=always`, `RestartSec=5` |

The unit is a *user* unit, and lingering is enabled (`loginctl show-user <user> -p Linger` → `yes`), so the gateway
starts at boot without a login session and survives logout.

## Process Architecture

```
systemd --user  →  hermes-gateway.service
                     └── hermes gateway run            (one process per host)
                           ├── Discord adapter         ← outbound/inbound messages
                           ├── session store           → state.db, sessions/
                           ├── agent loop              → model provider API
                           └── tools                   → shell, files, kubectl, git, browser
```

- The gateway is **one process for the whole host**, not one per chat. Sessions are keyed per Discord channel/thread.
- Each agent turn runs with the toolset configured for the originating platform (`platform_toolsets`), so a Discord
  turn gets the Discord toolset, not the CLI one.
- Model calls leave the host to the configured provider; nothing is served locally. There is no model server in the
  cluster, so cluster GPU workloads and Hermes do not interact.
- The agent is not a cluster client in the Kubernetes sense — it uses the host kubeconfig and runs `kubectl` like a
  human operator would, which means its permissions are the kubeconfig's permissions.

## What Hermes Is Allowed To Do

- Read and write the `k8s-home` checkout, and open pull requests against it.
- Run `kubectl`, `helm`, and read-only node commands as the `suvanjan` user.
- Create and comment on issues and pull requests as a GitHub App bot identity.

Standing rules enforced by convention, documented here so a reader knows what to expect in the git history:

- **Never push to `main`.** All changes go through a pull request for review.
- **Never commit secrets.** The repositories are public; credentials live only in `~/.hermes/.env` and on disk.
- Destructive actions (restarts, upgrades, reboots) are performed deliberately, not as a side effect of a question.

## Relationship to the Rest of This Repository

| Document | Relevance to Hermes |
|---|---|
| [bootstrap.md](../bootstrap.md) | How the node itself was built; Hermes assumes this is already done |
| [k8s-manifests.md](../k8s-manifests.md) | Layout Hermes edits when it changes an application |
| [upgrade.md](../upgrade.md) | Cluster upgrades, which Hermes may drive but with human review |
