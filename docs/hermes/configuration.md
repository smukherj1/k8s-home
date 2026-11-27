# Hermes Configuration

Hermes keeps state in one directory, `HERMES_HOME` (here `~/.hermes`). Two files matter:

| File | Contents | Handling |
|---|---|---|
| `~/.hermes/config.yaml` | Settings. Plain, commented YAML. Not secret. | Edit with `hermes config set <key> <value>` |
| `~/.hermes/.env` | Credentials only. | Edit by hand, `chmod 600`, never commit |

Do not hand-edit `config.yaml`. A stray indent corrupts the file and the running gateway will not pick it up cleanly.
Use:

```shell
hermes config get <key>
hermes config set <key> <value>
```

Command-line flags (`--model`, `--provider`, `-t/--toolsets`) override the file for a single invocation.

## Model and Provider

The model is selected interactively and stored under `model:` — `model.default` is the model slug, `model.provider`
the inference backend (`openrouter` here, with `model.base_url` pointing at the OpenRouter API). Credentials come from
`OPENROUTER_API_KEY` in `.env`.

```shell
# Switch the default model/provider
hermes model

# Show what is actually in effect
hermes status
```

Model changes take effect on the next turn; the running gateway does not need a restart for a `config.yaml` edit.

## Behaviour Knobs Worth Knowing

The full file is self-documented, but these are the ones that change how the agent behaves day to day:

| Key | Current | Effect |
|---|---|---|
| `agent.max_turns` | `150` | Tool-calling iterations per turn. Raising it raises token spend. |
| `agent.clarify_timeout` | `600` | Seconds a question to a human stays open before the turn continues unanswered. |
| `approvals.destructive_slash_confirm` | `false` | Whether destructive slash commands prompt for confirmation. |
| `memory.memory_char_limit` | `2200` | Agent note budget, injected into every turn. |
| `memory.user_char_limit` | `1375` | User-profile budget. |
| `skills.creation_nudge_interval` | `15` | Reminds the agent to save a skill every N tool calls; `0` disables. |
| `compression.*` | defaults | Context compression thresholds and summariser model. |
| `delegation.*` | defaults | Sub-agent concurrency and background task behaviour. |
| `timezone` | `America/New_York` | Timestamps in prompts, cron, and logs. |

Memory and skills are the two things that make the agent useful between sessions; both live on disk and both are
included in the backup procedure in [operations.md](operations.md#backup-and-restore).

## Platforms and the Gateway

Discord is the only configured platform. Enabling it takes three things:

1. `DISCORD_BOT_TOKEN` in `~/.hermes/.env`.
2. `DISCORD_ALLOWED_USERS` in `.env` — the allowlist of Discord user IDs permitted to talk to the bot. With
   `gateway.allow_all_users: false` (the setting here), anyone not on that list is ignored.
3. `platform_toolsets.discord` in `config.yaml` naming the toolset the agent gets on that platform
   (`[hermes-discord]` here).

```shell
# Reconfigure platforms interactively (writes to config.yaml / .env)
hermes gateway setup

# Which profiles have a gateway, and is it up
hermes gateway list
hermes gateway status
```

The gateway process itself, the service unit, and restart behaviour are covered in
[operations.md](operations.md#service-control).

## Toolsets

Toolsets are named groups of tools (`hermes-discord`, `hermes-cli`, etc.) selected per platform via
`platform_toolsets`. The toolset decides what the agent *can* do in a given conversation — a CLI turn and a Discord
turn do not have to expose the same tools. To list what is available:

```shell
hermes --help            # top-level flags, including -t/--toolsets
```

The agent's access to this host is therefore bounded by three layers: the toolset, Unix permissions of the `suvanjan`
user, and the approval mode.

## Skills

Skills are procedural memory: markdown files the agent loads on demand when a task matches. They live in
`~/.hermes/skills/<category>/<skill>/SKILL.md` — currently ~45 skills across 13 categories (`devops`, `host-admin`,
`software-development`, `research`, `productivity`, and others).

- Skills are loaded by relevance, not all at once, so an unused skill costs nothing per turn.
- The agent can create and patch skills itself; that is how a workflow learned once survives into later sessions.
- Individual skills can be disabled without deleting them:

```shell
hermes config get skills.disabled
hermes config set skills.disabled '["skill-a", "skill-b"]'
```

Because skills encode the operator's preferred procedure, `~/.hermes/skills/` is part of the backup set, not
disposable cache.

## Plugins

Hermes ships bundled plugins (provider adapters, messaging platforms, browser and web-search backends) and enables
most of them by default — 64 registered, 59 enabled on this host. Only one is **user-installed**:

`github_app` (`~/.hermes/plugins/github_app`) — listed under `plugins.enabled` in `config.yaml`. It contributes seven
tools (`github_identity`, `github_create_issue`, `github_comment_issue`, `github_list_issues`, `github_get_issue`,
`github_review_pr`, `github_merge_pr`) and one `pre_tool_call` hook that resolves the bot identity and attaches
attribution to every result.

```shell
hermes plugins list                 # everything, with status
hermes plugins list --enabled       # enabled only
hermes plugins list --user          # non-bundled only — the set that needs backing up
```

Plugin installs can be given a longer clone deadline with `plugins.clone_timeout_seconds`; unused plugins are removed
from `plugins.enabled` rather than uninstalled, so the bundled copies stay on disk.

## GitHub Authentication

There is **no personal access token anywhere** on this host. GitHub access is a GitHub App installation:

- The plugin authenticates as the App installation for API tools (issues, PR reviews, comments).
- `git` authenticates through a credential helper that mints a short-lived installation token on demand:

```shell
# Already configured globally; shown for reference
git config --global --get-regexp credential
# credential.https://github.com.helper !/home/suvanjan/.hermes/bin/git-credential-github-app.py
# credential.https://github.com.usehttppath true
```

Environment variables the plugin and helper read from `~/.hermes/.env`:

| Variable | Purpose |
|---|---|
| `GITHUB_APP_ID` | App identifier |
| `GITHUB_APP_INSTALLATION_ID` | Installation on the account/org |
| `GITHUB_APP_PRIVATE_KEY_PATH` | Path to the App private key (`chmod 600`) |
| `GITHUB_APP_PRIVATE_KEY` | Alternative inline key (unused here) |
| `GITHUB_APP_SLUG` | Optional; used for identity display |

Tokens are cached under `~/.hermes/cache` until they expire, in a `0600` file. Nothing long-lived is written to disk.

Consequences worth knowing:

- Rotating the App private key means replacing the file named by `GITHUB_APP_PRIVATE_KEY_PATH`; git picks it up on
  the next token mint. No `git config` change is needed.
- If a clone or push fails with an auth error, the first check is the helper directly — see
  [operations.md](operations.md#troubleshooting).
- The App's permissions bound what the agent can do to GitHub. It cannot exceed the installation scope, which is the
  main reason to prefer this over a personal token.

## Secret Handling Rules

- Credentials only in `~/.hermes/.env`; settings only in `config.yaml`. A non-credential setting placed in `.env` will
  not be read as configuration.
- The cloned repositories are public. Never write a token, key, webhook URL, or credential-bearing URL into a commit,
  a document, an issue, or a pull request — including this repository.
- `.env` is `0600` and is backed up separately from the repo; treat any copy of it as sensitive.
