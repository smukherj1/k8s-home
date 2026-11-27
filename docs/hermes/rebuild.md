# Appendix: Rebuilding the Hermes Setup

Rebuild the agent from a bare Ubuntu install. This is the disaster-recovery path and the "how was this actually set
up" reference — not the normal operating procedure, which is in [operations.md](operations.md).

Target state: the gateway running as a user service on the node, answering in Discord, authenticating to GitHub as a
GitHub App, with the previous configuration, skills, and memories restored, and passwordless sudo in place for host
administration.

## Before Starting

1. Confirm the node is already built per [bootstrap.md](../bootstrap.md) — k3s, helm, and `kubectl` should work.
2. Have these available. They are **not** recoverable from the repositories:
   - The Hermes backup archive (`hermes backup` output), or a copy of `~/.hermes`.
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

The installer tracks the upstream release channel, so a rebuild gets whatever is current, not the version that was
running before. Record `hermes --version` alongside each backup so that delta is at least visible after a restore.

## Step 2: Restore Configuration Before First Run

Restoring first avoids re-answering setup prompts and re-keying credentials.

```shell
hermes backup     # on the old machine, if it still exists
hermes import <archive>
```

If nothing is restorable, continue with Steps 3–6 and rebuild the configuration by hand; expect to lose skills,
memories, and session history.

Verify the restored files are in place and sane, including the disabled-skill list (configuration, restored with
`config.yaml` — there is no separate list to keep):

```shell
hermes config get model.default
hermes config get platform_toolsets.discord
hermes config get skills.disabled
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

## Step 8: Passwordless Sudo for Host Administration

The agent reboots the host, controls systemd units, and installs packages. Interactive `sudo` cannot work from a
non-interactive agent turn, so the operator account gets a **scoped** `NOPASSWD` drop-in — not blanket root. The full
file is [90-suvanjan-nopasswd.sudoers](90-suvanjan-nopasswd.sudoers); it allows exactly:

- `systemctl reboot`, `systemctl poweroff`
- `systemctl start|stop|restart|reload|enable|disable <unit…>`
- `apt update`, `apt upgrade [-y]`, `apt autoremove [-y]`, `apt install|remove|purge [-y] <package…>`

Arguments after the subcommand are matched by regex (`^…$`, sudo ≥ 1.9.10). Package and unit names must begin with a
letter or digit, which blocks option smuggling such as `-o DPkg::Pre-Invoke=…` or `--root=…`. Anything outside these
patterns still prompts for a password and therefore fails.

Install it — validate first, then place it with the ownership and mode sudo requires (`0440 root:root`, and no `.` in
the filename, or sudo silently ignores it):

```shell
# Parse the file before it can break sudo for the whole machine
visudo -c -f docs/hermes/90-suvanjan-nopasswd.sudoers

# Install at the path the docs and the agent's skill refer to
sudo install -m 0440 -o root -g root \
  docs/hermes/90-suvanjan-nopasswd.sudoers /etc/sudoers.d/90-suvanjan-nopasswd
```

Never edit the installed file with a redirect: a malformed sudoers file locks out `sudo` entirely. Change the file in
the repository, re-validate, and reinstall.

Test it — three checks, all non-interactive:

```shell
# 1. The rules are present, and there is no NOPASSWD: ALL
sudo -n -l

# 2. Out-of-scope commands still require a password (expected: "sudo: a password is required")
sudo -n true

# 3. An allowed command runs without a prompt
sudo -n apt update
```

`sudo -n true` failing is the correct result, not a fault: it proves the scope is enforced rather than bypassed.

The `systemctl` rules in the drop-in cover **system** units only. Hermes' own gateway is a *user* unit and is managed
with `systemctl --user` as `suvanjan`, never with `sudo`. Run `sudo -n -l` after any edit to confirm the effective
policy, since the installed file is not readable by the user.

## Step 9: Verify

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
5. Ask it to run `sudo -n apt update` from a turn — verifies the sudo drop-in from Step 8.
