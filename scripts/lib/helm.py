import os
import requests
import yaml
from packaging.version import Version, InvalidVersion

def is_oci(url: str) -> bool:
    return url.startswith("oci://")

def latest_from_http_repo(repo_url: str, chart: str) -> str:
    index_url = repo_url.rstrip("/") + "/index.yaml"

    r = requests.get(index_url, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"failed to fetch index.yaml from {index_url}")

    index = yaml.safe_load(r.text)
    entries = index.get("entries", {})

    if chart not in entries:
        raise RuntimeError(f"chart '{chart}' not found in repo")

    versions = entries[chart]
    if not versions:
        raise RuntimeError(f"no versions found for chart '{chart}'")

    # Helm spec: newest first
    return versions[0]["version"]

def latest_from_oci_repo(oci_url: str, chart: str) -> str:
    ref = oci_url.removeprefix("oci://").rstrip("/")
    parts = ref.split("/", 1)

    if len(parts) != 2:
        raise RuntimeError("invalid OCI repo URL")

    registry, repo = parts

    # chart name must match final path element
    if not repo.endswith("/" + chart) and repo != chart:
        repo = repo.rstrip("/") + "/" + chart

    tags_url = f"https://{registry}/v2/{repo}/tags/list"
    headers = {}
    if registry == "ghcr.io":
        headers["Authorization"] = "Bearer " + os.getenv("GITHUB_BASIC_AUTH")

    r = requests.get(tags_url, timeout=10, headers=headers)
    if r.status_code == 404:
        raise RuntimeError(f"OCI repo not found: {repo}")
    if r.status_code != 200:
        raise RuntimeError(f"failed to fetch tags from {tags_url} ({r.status_code}): {r.text}")

    tags = r.json().get("tags", [])
    if not tags:
        raise RuntimeError("no tags found")

    versions = []
    for tag in tags:
        try:
            v = Version(tag.lstrip("v"))
            if v.is_prerelease or v.is_devrelease:
                continue
            versions.append((v, tag))
        except InvalidVersion:
            pass

    if not versions:
        raise RuntimeError("no semver-compatible tags found")

    versions.sort(reverse=True)
    return versions[0][1]

def get_latest_version(repo_url: str, chart: str) -> str:
    """Fetches the latest version for a given Helm chart and repo URL."""
    if is_oci(repo_url):
        return latest_from_oci_repo(repo_url, chart)
    else:
        return latest_from_http_repo(repo_url, chart)
