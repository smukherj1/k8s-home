#!/usr/bin/env python3

import sys
import re
import requests
import yaml
import os
from packaging.version import Version, InvalidVersion

def die(msg):
    raise RuntimeError(msg)

def is_oci(url: str) -> bool:
    return url.startswith("oci://")

def latest_from_http_repo(repo_url: str, chart: str) -> str:
    index_url = repo_url.rstrip("/") + "/index.yaml"

    r = requests.get(index_url, timeout=10)
    if r.status_code != 200:
        die(f"failed to fetch index.yaml from {index_url}")

    index = yaml.safe_load(r.text)
    entries = index.get("entries", {})

    if chart not in entries:
        die(f"chart '{chart}' not found in repo")

    versions = entries[chart]
    if not versions:
        die(f"no versions found for chart '{chart}'")

    # Helm spec: newest first
    return versions[0]["version"]

def latest_from_oci_repo(oci_url: str, chart: str) -> str:
    ref = oci_url.removeprefix("oci://").rstrip("/")
    parts = ref.split("/", 1)

    if len(parts) != 2:
        die("invalid OCI repo URL")

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
        die(f"OCI repo not found: {repo}")
    if r.status_code != 200:
        die(f"failed to fetch tags from {tags_url} ({r.status_code}): {r.text}")

    tags = r.json().get("tags", [])
    if not tags:
        die("no tags found")

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
        die("no semver-compatible tags found")

    versions.sort(reverse=True)
    return versions[0][1]

def main():
    if len(sys.argv) != 3:
        print("usage: helm-latest-version <repo-url> <chart-name>", file=sys.stderr)
        sys.exit(2)

    repo_url = sys.argv[1]
    chart = sys.argv[2]

    if is_oci(repo_url):
        version = latest_from_oci_repo(repo_url, chart)
    else:
        version = latest_from_http_repo(repo_url, chart)

    print(version)

if __name__ == "__main__":
    main()
