# Application Kubernetes Manifests

The application kubernetes manifests are located in the `applications` directory. The YAML files directly under
this directory are the manifests for the ArgoCD applications.

Under the `applications` directory, there are subdirectories for each application with the same name as the
application manifest (without the .yml extension).

## Updating Helm Chart Versions

To keep the fleet up to date, there is a script to automatically check for and apply updates to Helm chart versions
referenced in the ArgoCD manifests.

### Running Updates

You can run the update script from the root of the repository:

```bash
# Preview changes without applying them
./scripts/update-helm-versions.py --dry-run

# Apply updates to the manifests
./scripts/update-helm-versions.py
```

The script will:
1. Scan all `.yml` files in the `applications/` directory.
2. Identify resources of type `Application` that use Helm charts.
3. Fetch the latest stable version for each chart.
4. Update the `targetRevision` in the YAML files if a newer version is available.

## Technical Documentation: Helm Update Scripts

The update process is powered by two Python scripts.

### `scripts/update-helm-versions.py`

This is the main orchestrator script. It handles the I/O and manifest manipulation.

- **Manifest Parsing**: It uses `ruamel.yaml` to parse and write YAML files. This preserves
  comments, quotes, and block styles, ensuring that the automated updates don't create "noisy" diffs in Git.
- **Chart Discovery**: It scans both `spec.source` and `spec.sources` in ArgoCD Application manifests,
  supporting both single-source and multi-source configurations.
- **Coordination**: It identifies unique chart/repo pairs and calls `helm-latest-version.py` for each to avoid
  redundant network calls.

### `scripts/helm-latest-version.py`

Queries the latest version of a specific chart.

- **Repository Support**:
    - **Standard HTTP**: Fetches and parses the `index.yaml` from traditional Helm repositories.
    - **OCI Registry**: Uses the Docker Distribution API v2 (`tags/list` endpoint) to query versions from
      registries like `ghcr.io` or `public.ecr.aws`.
- **Version Selection**: 
    - It uses the `packaging.version` library to parse tags.
    - It automatically filters out pre-releases, alpha, beta, and release candidates to ensure only stable
      versions are suggested.
    - Tags are sorted according to SemVer rules to determine the "latest".
- **Authentication**: For GitHub Container Registry (`ghcr.io`), it supports using a `GITHUB_BASIC_AUTH`
  environment variable to handle rate limits or private repositories.