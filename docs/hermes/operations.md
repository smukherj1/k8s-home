# Operating Hermes

Runbook for the Hermes gateway on this node. Assumes the install described in
[overview.md](overview.md) and the configuration in [configuration.md](configuration.md).

## Service Control

Hermes runs as a **user** unit (`systemctl --user`), not a system unit. Never use `sudo systemctl` for it.

```shell
# Status, via systemd
systemctl --user status hermes-gateway

# Status, via Hermes (resolves the service, its version, and platforms)
hermes gateway status

# Restart / stop / start
systemctl --user restart hermes-gateway
systemctl --user stop hermes-gateway
systemctl --user start hermes-gateway

# Which profiles have a gateway, and their state
hermes gateway list
```

The unit is `Restart=always` with `RestartSec=5`, so a crash recovers on its own within seconds. A manual `stop` is
the only way to keep it down.

Restarts are graceful for in-flight conversations: `KillMode=mixed` plus `TimeoutStopSec=70` gives the gateway up to
70 seconds to unwind, and `RestartForceExitStatus=75` is treated as a normal exit so restarts do not trip the start
limit.

### Host-Level Operations

Beyond this service and the cluster, the agent can reboot or power off the host, control **system** units, and manage
apt packages, through a scoped `NOPASSWD` sudoers drop-in (`/etc/sudoers.d/90-suvanjan-nopasswd`, documented in
[rebuild.md](rebuild.md#step-8-passwordless-sudo-for-host-administration)). It is not blanket root: commands outside
the listed patterns still need a password and therefore fail inside an agent turn with `sudo: a password is required`.
That error means "out of scope", not "broken".

### Emergency Stop

If the agent is stuck in a loop, burning tokens, or should not act while you repair something:

```shell
# Stop accepting new gateway turns and pause cron/kanban dispatch
hermes pause

# Undo
hermes resume
```

`hermes pause` is a state flag, not a process stop — the gateway stays up and `hermes resume` returns it to normal
service without a restart. Use `systemctl --user stop` only when you want the process gone entirely.

## Health Checks

```shell
# Model, provider, gateway state, platforms, job count
hermes status
hermes status --full     # every section

# Configuration and dependency checks
hermes doctor

# Version and install method
hermes --version
```

`hermes status` is the first thing to run for "is it working?" — it distinguishes a dead gateway from a working
gateway with a bad model configuration.

## Logs

| Path | Contents |
|---|---|
| `~/.hermes/logs/gateway.log` | Gateway lifecycle, platform connect/disconnect, inbound routing |
| `~/.hermes/logs/agent.log` | Agent turns, tool calls, model requests |
| `~/.hermes/logs/errors.log` | Errors only; the first file to read after a failure |
| `~/.hermes/logs/gateway-exit-diag.log` | Restart/exit diagnostics — use after a crash loop |

```shell
# Unit's stdout/stderr (includes startup failures)
journalctl --user -u hermes-gateway -n 200 --no-pager
journalctl --user -u hermes-gateway -f

# Hermes' own filtered log viewer
hermes logs
```

Startup failures often appear in the journal and nowhere else, because the process dies before it can write its own
logs.

## Updating

The install is git-based, so updates pull from the Hermes repository and reinstall dependencies:

```shell
# Is there anything new?
hermes update --check

# What would be touched, including which services get restarted
hermes update --plan

# Apply
hermes update
```

**Behaviour as it stands:** `hermes update` moves the install to the latest version on its channel, with no version
pinning and no automatic rollback. The checkout is not a fork, so a revert means checking out an older commit manually
and reinstalling dependencies — there is no supported "downgrade to previous release" step documented here.

Because the update replaces code under a running gateway, **expect the Discord bot to be unavailable during the
update**, and expect any in-flight agent turn to be cut. Sequence it as:

1. `hermes update --plan` and read what will restart.
2. `hermes update`.
3. `hermes status` and `systemctl --user status hermes-gateway`.
4. Send a test message in Discord.
5. If it did not come back: `journalctl --user -u hermes-gateway -n 100`, then `hermes doctor`.

Take a backup (below) before updating if there is anything in `~/.hermes` you would not want to reconstruct.

## Backup and Restore

Nothing backs Hermes up automatically today. **Hermes is not in Argo CD**, so a lost `~/.hermes` is not recovered by
any reconciliation loop — it is recovered by this section.

### Backup

```shell
hermes backup
```

That zips the home directory, which is the whole of the agent's state — settings, `.env`, skills, plugins, memories,
session history. Nothing is backed up selectively here because nothing under `~/.hermes` is disposable.

Two things are outside `~/.hermes` and therefore outside the archive: the git credential configuration
(`~/.gitconfig`, reinstalled per [rebuild.md](rebuild.md#step-5-github-app-and-git-authentication)) and the sudoers
drop-in ([rebuild.md](rebuild.md#step-8-passwordless-sudo-for-host-administration)). The `~/.hermes/hermes-agent`
checkout is also excluded by design — it is re-installable.

The archive contains `.env`, so it is a credential store: keep it off the public repositories and treat it with the
same care as the file itself.

### Restore

```shell
hermes import <archive>
systemctl --user restart hermes-gateway
```

After a restore, verify: `hermes doctor`, `hermes gateway status`, then a test Discord message. If GitHub operations
fail, check that the private key named by `GITHUB_APP_PRIVATE_KEY_PATH` exists and is `0600` — the path is restored
from `.env`, but the key file may not be, depending on where it was stored.

## Troubleshooting

| Symptom | First checks | Usual cause |
|---|---|---|
| Bot silent in Discord | `hermes gateway status`; `journalctl --user -u hermes-gateway -n 100` | Process down, or bot token invalid/revoked |
| Gateway running but ignores you | `hermes config get gateway.allow_all_users`; check `DISCORD_ALLOWED_USERS` in `.env` | Your Discord user ID is not on the allowlist |
| Restart loop | `~/.hermes/logs/gateway-exit-diag.log`; journal | Broken config edit, failed update, port/socket conflict |
| Model errors / 401 / 429 | `hermes status`; `hermes doctor`; provider dashboard | Bad or exhausted `OPENROUTER_API_KEY`, provider rate limit |
| Turns hang until timeout | `~/.hermes/logs/agent.log`; `hermes pause` then `resume` | Provider stall, or a tool waiting on a human answer |
| `git clone`/`push` fails auth | Run the helper directly (below) | App key missing, rotated, or installation revoked |
| Browser tooling fails | `hermes doctor`; `hermes tools` | Chromium shared-library/runtime problem on the host |
| Update broke the gateway | `hermes update --plan`; journal; reinstall deps | Upstream regression — no pinning exists, so recovery is manual |

### Testing GitHub auth directly

The credential helper is a standalone script, so it can be exercised without git:

```shell
printf 'protocol=https\nhost=github.com\n\n' \
  | ~/.hermes/bin/git-credential-github-app.py get | sed 's/^password=.*/password=<redacted>/'
```

A working setup prints `username=...` and a password line. The password is a short-lived installation token — never
paste it anywhere; the `sed` above redacts it for safe sharing.

If this fails, the cause is one of `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, or the private key file named by
`GITHUB_APP_PRIVATE_KEY_PATH` in `~/.hermes/.env`.

## Routine Checks

Worth doing occasionally, all read-only:

```shell
hermes --version            # is the install current
hermes status --full
hermes insights             # usage/token analytics
hermes usage                # provider rate-limit windows
du -sh ~/.hermes/state.db   # session store growth
hermes sessions prune       # if history growth is a problem
```
