# Appendix: Rebuilding the Hermes Setup

Rebuild the agent from a bare Ubuntu install. This is the disaster-recovery path and the "how was this actually set
up" reference — not the normal operating procedure, which is in [operations.md](operations.md).

Target state: the gateway running as a user service on the node, answering in Discord, authenticating to GitHub as a
GitHub App, with the previous configuration, skills, and memories restored.

## Before Starting

1. Confirm the node is already built per [bootstrap.md](../bootstrap.md) — k3s, helm, and `kubectl` should work.
2. Have these available. They are **not** recoverable from the repositories:
   - The Hermes backup archive (`hermes backup` output), or a copy of `~/.hermes/{config.yaml,.env,skills,memories,plugins,bin}`.
   - The GitHub App private key (`.pem`), and its App ID and installation ID.
   - The Discord bot token.
   - A model provider API key (OpenRouter here).
3. Confirm `curl`, `git`, and Python 3 are present.

## Step 1: Install Hermes Agent

```shell
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

This bootstraps the package manager, the Python runtime under `~/.hermes/tools/`, and the `hermes` launcher, then
installs the source to `~/.hermes/hermes-agent`.

```shell
hermes --version     # confirm the install and its method (git)
```

## Step 2: Restore Configuration Before First Run

Restoring first avoids re-answering setup prompts and re-keying credentials.

```shell
# Full restore, if a `hermes backup` archive exists
hermes import <archive>

# Otherwise, restore the subset that matters
tar -xzf <backup>.tar.gz -C ~/.hermes
chmod 600 ~/.hermes/.env
```

If nothing is restorable, continue with Steps 3–6 and rebuild the configuration by hand; expect to lose skills,
memories, and session history.

Verify the two files are in place and sane:

```shell
hermes config get model.default
hermes config get platform_toolsets.discord
```

## Step 3: Model and Provider

```shell
# Interactive model/provider selection (writes model.default / model.provider)
hermes model
```

The API key belongs in `~/.hermes/.env`, never in `config.yaml`:

```shell
# ~/.hermes/.env  (chmod 600)
OPENROUTER_API_KEY=<provider key>
```

## Step 4: Discord

1. Create (or reuse) the bot application in the Discord developer portal and copy the bot token.
2. Invite the bot to the server with permission to read and send messages in the target channel.
3. Write the credentials and allowlist to `~/.hermes/.env`:

```shell
DISCORD_BOT_TOKEN=<bot token>
DISCORD_ALLOWED_USERS=<your numeric Discord user id>
```

4. Configure the platform so that the token is picked up and the toolset is assigned:

```shell
hermes gateway setup     # select Discord; writes config.yaml and .env
hermes config get gateway.allow_all_users     # should be false
```

The allowlist is the access control: a user ID that is not listed is ignored even though the bot is connected.

## Step 5: GitHub App and Git Authentication

GitHub access is an App installation, never a personal access token — the repositories are public and a personal token
would over-grant.

1. Create a GitHub App, install it on the account or organisation that owns this repository, and grant it repository
   contents (read/write), issues (read/write), and pull requests (read/write).
2. Download the private key and store it outside the repository, `chmod 600`.
3. Put the identifiers in `~/.hermes/.env`:

```shell
GITHUB_APP_ID=<app id>
GITHUB_APP_INSTALLATION_ID=<installation id>
GITHUB_APP_PRIVATE_KEY_PATH=/home/suvanjan/.hermes/github-app.pem
```

4. Install the credential helper and point git at it:

```shell
mkdir -p ~/.hermes/bin
# place git-credential-github-app.py here (restored from backup, or recreated)

git config --global credential.https://github.com.helper \
  '!/home/suvanjan/.hermes/bin/git-credential-github-app.py'
git config --global credential.https://github.com.usehttppath true
```

5. Verify the helper mints a token before involving git:

```shell
printf 'protocol=https\nhost=github.com\n\n' \
  | ~/.hermes/bin/git-credential-github-app.py get | sed 's/^password=.*/password=<redacted>/'
```

6. Enable the `github_app` plugin so the agent has the GitHub tools:

```shell
hermes plugins list --user
hermes config get plugins.enabled    # should include github_app
```

## Step 6: Clone the Working Repositories

```shell
mkdir -p ~/depot
git clone https://github.com/smukherj1/k8s-home.git ~/depot/k8s-home
```

The clone should authenticate through the helper from Step 5 — no token in the URL, no interactive prompt.

## Step 7: Install the Gateway Service

```shell
hermes gateway install      # writes ~/.config/systemd/user/hermes-gateway.service
systemctl --user daemon-reload
systemctl --user enable --now hermes-gateway
loginctl enable-linger "$USER"
```

Lingering is what makes the *user* unit start at boot and survive logout. Without it the bot only runs while that user
has a login session.

## Step 8: Verify

```shell
hermes status
hermes gateway status
systemctl --user status hermes-gateway
```

Then, in order:

1. Send a message in Discord and confirm a reply.
2. Ask the agent to read a file in `~/depot/k8s-home` — verifies the working directory and shell access.
3. Ask it to list open issues on the repository — verifies the GitHub App path.
4. Confirm `kubectl get nodes` works from a turn — verifies node access.

## What Is Not Automatable

Worth stating plainly, because this is the reason the appendix exists at all:

- **No declarative config.** `config.yaml` is not in this repository and nothing reconciles it. A rebuild is a restore,
  not a `git apply`.
- **Secrets are out of band.** The App private key, Discord token, and provider key exist only outside the repos. Their
  loss means reissuing all three.
- **No version pinning.** The install tracks the upstream channel; a rebuild gets whatever is current, not the version
  that was previously running. Record `hermes --version` alongside backups so the delta is at least visible.
- **Skills and memories are the agent's accumulated knowledge.** They are files, not repository content. Include them
  in backups or they are gone.
