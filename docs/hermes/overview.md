# Hermes Agent Overview

[Hermes Agent](https://hermes-agent.nousresearch.com/docs/) is the AI agent that operates this home lab. It runs on
the Kubernetes node, but **not** as a Kubernetes workload: it is a host-level systemd **user** service that talks to
Discord, works in the `k8s-home` git checkout, and has `kubectl`, git, and shell access to the node.

This document is the entry point. The details are split across:

- [configuration.md](configuration.md) — `config.yaml` vs `.env`, model/provider, platforms, skills, plugins, GitHub auth.
- [operations.md](operations.md) — start/stop/restart, health checks, logs, upgrades, backups, troubleshooting.
- [rebuild.md](rebuild.md) — appendix: rebuild the whole setup from a bare Ubuntu install.

## Why Hermes Is Not in Kubernetes

Everything else in this repository is reconciled into the cluster by Argo CD. Hermes deliberately is not.

The reason is scope: Hermes administers **the machine**, not just the cluster. It runs `apt`, controls systemd
services, reboots the host, and edits the manifests that Argo CD reconciles. Putting it inside the cluster would put
the tool that repairs the cluster under the control of the cluster — a broken k3s, a starving node, or a wedged
Argo CD would take the agent down with it, at exactly the moment it is needed. A host-level systemd **user** service
depends on none of that.

The trade-off: **Hermes is not declarative**. Its configuration is not in this repo and not reconciled by Argo CD.
Drift is possible; recovery is the backup and restore procedure in [operations.md](operations.md#backup-and-restore),
and the rebuild in [rebuild.md](rebuild.md).

## Runtime Inventory

Single profile (`default`), one gateway process, no cron jobs.

All of the agent's *state* — settings, `.env`, skills, plugins, memory, session history — lives under
`~/.hermes` (`HERMES_HOME`) and is captured by `hermes backup`; that is the whole backup story and it is not
re-listed here. The only parts of the install a backup does not cover:

| Component | Location | Notes |
|---|---|---|
| Agent install | `~/.hermes/hermes-agent` | git checkout, ~1.1 GB; re-created by the installer and moved by `hermes update`, so not part of a backup |
| Service unit | `~/.config/systemd/user/hermes-gateway.service` | re-created by `hermes gateway install` |

The unit is a *user* unit, and lingering is enabled (`loginctl show-user <user> -p Linger` → `yes`), so the gateway
starts at boot without a login session and survives logout.

Outside `~/.hermes` entirely, the only machine-level grant the agent relies on is the passwordless-sudo drop-in at
`/etc/sudoers.d/90-suvanjan-nopasswd` — no backup covers it; it is reinstalled per
[rebuild.md](rebuild.md#step-8-passwordless-sudo-for-host-administration).

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
- Run `kubectl`, `helm`, and shell commands as the `suvanjan` user.
- `sudo -n` for a fixed set of host-admin commands: `systemctl reboot|poweroff`, `systemctl
  start|stop|restart|reload|enable|disable <unit>`, and `apt update|upgrade|autoremove|install|remove|purge` with
  package-name arguments only. Everything else still requires a password and therefore fails in a non-interactive
  turn. The drop-in is in [/etc/sudoers.d/90-suvanjan-nopasswd](rebuild.md#step-8-passwordless-sudo-for-host-administration).
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
