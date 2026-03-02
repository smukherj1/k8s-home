#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from ruamel.yaml import YAML
from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel, validate_call

class HelmChartSource(BaseModel):
    """Information about a Helm chart source in an ArgoCD manifest."""
    repo_url: str
    chart: str
    target_revision: str
    path: List[Any]  # The path of keys/indices to reach targetRevision in the YAML data

class UpdateManifestTask(BaseModel):
    """A collection of Helm chart sources within a single manifest file that may need updates."""
    filename: str
    sources: List[HelmChartSource]

@validate_call
def get_latest_version(repo_url: str, chart: str) -> Optional[str]:
    """Calls scripts/helm-latest-version.py to get the latest version."""
    script_path = os.path.join(os.path.dirname(__file__), "helm-latest-version.py")
    try:
        result = subprocess.run(
            ["uv", "run", script_path, repo_url, chart],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting latest version for {chart} at {repo_url}: {e.stderr}", file=sys.stderr)
        return None

@validate_call
def extract_helm_sources_from_spec(spec: dict) -> List[Tuple[dict, List[Any]]]:
    """
    Extracts Helm sources and their access paths from an ArgoCD spec.
    'spec' is the 'spec' field of an ArgoCD Application manifest YAML.
    Returns a list of (source_dict, path_to_target_revision).
    """
    sources_data = spec.get('sources', [])
    # ArgoCD can have single 'source' or multiple 'sources'
    if not sources_data and 'source' in spec:
        sources_data = [spec['source']]
        base_path = ['spec', 'source']
        is_multiple = False
    else:
        base_path = ['spec', 'sources']
        is_multiple = True

    found = []
    for i, source in enumerate(sources_data):
        if source.get('repoURL') and source.get('chart') and source.get('targetRevision'):
            path = base_path + ([i, 'targetRevision'] if is_multiple else ['targetRevision'])
            found.append((source, path))
    return found

@validate_call
def get_chart_update_info(filename: str, data: dict) -> Optional[UpdateManifestTask]:
    """
    Extracts update information from an ArgoCD Application manifest.
    'data' is the entire ArgoCD Application manifest YAML.
    """
    if not data or data.get('kind') != 'Application':
        return None

    spec = data.get('spec', {})
    helm_sources = extract_helm_sources_from_spec(spec)
    
    sources = [
        HelmChartSource(
            repo_url=s['repoURL'],
            chart=s['chart'],
            target_revision=s['targetRevision'],
            path=p
        )
        for s, p in helm_sources
    ]

    if not sources:
        return None

    return UpdateManifestTask(filename=filename, sources=sources)

@validate_call
def collect_tasks(directory: str, yaml_loader: YAML) -> List[UpdateManifestTask]:
    """Scans the directory for manifests and collects update tasks."""
    tasks = []
    if not os.path.isdir(directory):
        print(f"Error: Directory {directory} does not exist.", file=sys.stderr)
        return tasks

    for filename in sorted(os.listdir(directory)):
        if not (filename.endswith(".yml") or filename.endswith(".yaml")):
            continue
        
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        with open(filepath, 'r') as f:
            try:
                data = yaml_loader.load(f)
                task = get_chart_update_info(filename, data)
                if task:
                    tasks.append(task)
            except Exception as e:
                # Use standard print for errors to match previous behavior
                print(f"Warning: Failed to parse {filename}: {e}", file=sys.stderr)
    
    return tasks

@validate_call
def fetch_latest_versions(tasks: List[UpdateManifestTask]) -> Dict[Tuple[str, str], str]:
    """Fetches the latest versions for all unique charts found in tasks.
    Returns a dictionary mapping (repo_url, chart) to the latest version.
    """
    unique_charts = set((s.repo_url, s.chart) for t in tasks for s in t.sources)
    
    latest_versions = {}
    print(f"Checking for updates for {len(unique_charts)} unique Helm charts...")
    for repo_url, chart in sorted(unique_charts):
        latest = get_latest_version(repo_url, chart)
        if latest:
            latest_versions[(repo_url, chart)] = latest
    return latest_versions

@validate_call
def apply_updates(directory: str, tasks: List[UpdateManifestTask], latest_versions: Dict[Tuple[str, str], str], dry_run: bool, yaml_loader: YAML):
    """Applies the updates to the manifest files.
    'directory' is the directory containing the manifests.
    'tasks' is a list of ArgoCD Application manifests being updated. Not all of them may actually have updates.
    'latest_versions' is a dictionary mapping (repo_url, chart) to the latest version.
    'dry_run' is a boolean indicating whether to dry run the updates.
    'yaml_loader' is a YAML loader object.
    """
    # Track which files need saving to avoid multiple writes.
    # Mapping from (filename) -> (updated YAML data)
    pending_updates: Dict[str, dict] = {}

    for task in tasks:
        filepath = os.path.join(directory, task.filename)
        
        for source in task.sources:
            latest = latest_versions.get((source.repo_url, source.chart))
            if not latest or source.target_revision == latest:
                continue

            print(f"{task.filename}: Update {source.chart} from {source.target_revision} to {latest}")
            
            if task.filename not in pending_updates:
                with open(filepath, 'r') as f:
                    pending_updates[task.filename] = yaml_loader.load(f)
            
            # Use the source.path to navigate to the targetRevision field in the pending_update data
            # and set it to the latest version.
            data = pending_updates[task.filename]
            for part in source.path[:-1]:
                data = data[part]
            data[source.path[-1]] = latest

    if not dry_run:
        for filename, data in pending_updates.items():
            filepath = os.path.join(directory, filename)
            with open(filepath, 'w') as f:
                yaml_loader.dump(data, f)
            print(f"Updated {filename}")
    
    if pending_updates:
        if dry_run:
            print("\nDry run completed. No files were modified.")
    else:
        print("\nAll charts are up to date.")

def main():
    parser = argparse.ArgumentParser(description="Update Helm chart versions in ArgoCD manifests.")
    parser.add_argument("--dry-run", action="store_true", help="Print updates without modifying files.")
    parser.add_argument("--dir", default="applications", help="Directory containing manifests.")
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    tasks = collect_tasks(args.dir, yaml)
    if not tasks:
        print("No Helm charts found to update.")
        return

    latest_versions = fetch_latest_versions(tasks)
    apply_updates(args.dir, tasks, latest_versions, args.dry_run, yaml)

if __name__ == "__main__":
    main()
