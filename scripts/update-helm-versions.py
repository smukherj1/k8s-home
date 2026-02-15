#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from ruamel.yaml import YAML
from typing import Dict, List, Tuple

def get_latest_version(repo_url: str, chart: str) -> str:
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

def main():
    parser = argparse.ArgumentParser(description="Update Helm chart versions in ArgoCD manifests.")
    parser.add_argument("--dry-run", action="store_true", help="Print updates without modifying files.")
    parser.add_argument("--dir", default="applications", help="Directory containing manifests.")
    args = parser.parse_args()

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    manifest_files = [f for f in os.listdir(args.dir) if f.endswith(".yml") and os.path.isfile(os.path.join(args.dir, f))]
    
    # Collect unique helm chart details
    # Map (repoURL, chart) -> current_versions (list of (file, path_to_revision))
    charts_to_update: Dict[Tuple[str, str], List[Tuple[str, List[str]]]] = {}

    for filename in manifest_files:
        filepath = os.path.join(args.dir, filename)
        with open(filepath, 'r') as f:
            try:
                data = yaml.load(f)
            except Exception as e:
                print(f"Warning: Failed to parse {filename}: {e}", file=sys.stderr)
                continue

            if not data or data.get('kind') != 'Application':
                continue

            spec = data.get('spec', {})
            sources = spec.get('sources', [])
            
            # ArgoCD can have single 'source' or multiple 'sources'
            if not sources and 'source' in spec:
                sources = [spec['source']]

            for i, source in enumerate(sources):
                repo_url = source.get('repoURL')
                chart = source.get('chart')
                target_revision = source.get('targetRevision')

                if repo_url and chart and target_revision:
                    key = (repo_url, chart)
                    if key not in charts_to_update:
                        charts_to_update[key] = []
                    
                    # Store where to find this revision
                    # For multiple sources, it's spec.sources[i].targetRevision
                    # For single source, it's spec.source.targetRevision
                    if 'sources' in spec:
                        path = ['spec', 'sources', i, 'targetRevision']
                    else:
                        path = ['spec', 'source', 'targetRevision']
                    
                    charts_to_update[key].append((filename, path, target_revision))
    print(f"Found {charts_to_update}")
    if not charts_to_update:
        print("No Helm charts found to update.")
        return

    # Find latest versions
    latest_versions: Dict[Tuple[str, str], str] = {}
    print(f"Checking for updates for {len(charts_to_update)} unique Helm charts...")
    for (repo_url, chart) in charts_to_update.keys():
        latest = get_latest_version(repo_url, chart)
        if latest:
            latest_versions[(repo_url, chart)] = latest

    # Update files
    files_to_update = {} # filename -> data

    for (repo_url, chart), targets in charts_to_update.items():
        latest = latest_versions.get((repo_url, chart))
        if not latest:
            continue

        for filename, path, current in targets:
            # Simple semver check (optional, but good for OCI tags with 'v' prefix)
            if current != latest:
                print(f"{filename}: Update {chart} from {current} to {latest}")
                
                if filename not in files_to_update:
                    filepath = os.path.join(args.dir, filename)
                    with open(filepath, 'r') as f:
                        files_to_update[filename] = yaml.load(f)
                
                # Navigate to the targetRevision in the data
                curr_data = files_to_update[filename]
                for part in path[:-1]:
                    curr_data = curr_data[part]
                curr_data[path[-1]] = latest

    if not args.dry_run:
        for filename, data in files_to_update.items():
            filepath = os.path.join(args.dir, filename)
            with open(filepath, 'w') as f:
                yaml.dump(data, f)
            print(f"Updated {filename}")
    elif files_to_update:
        print("\nDry run completed. No files were modified.")
    else:
        print("\nAll charts are up to date.")

if __name__ == "__main__":
    main()
