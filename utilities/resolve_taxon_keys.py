#!/usr/bin/env python3
"""
Resolves scientific names to Catalogue of Life taxon keys. Useful for experimenting
with recipes that use GBIF as a datasource. Example usage:

    python resolve_taxon_keys.py 'Canis lupus' 'Cervus elaphus' 'Sus scrofa' 'Capreolus capreolus'

"""

import argparse
import json
import urllib.parse
import urllib.request

# Catalogue of Life Extended Release - the checklist GBIF now keys occurrences on.
COL_XR = "7ddf754f-d193-4cc9-b351-99906754a03b"
MATCH_URL = "https://api.gbif.org/v2/species/match"


def match(name, checklist):
    params = urllib.parse.urlencode({"scientificName": name, "checklistKey": checklist})
    with urllib.request.urlopen(f"{MATCH_URL}?{params}", timeout=30) as r:
        return json.load(r)


def pick_key(resp):
    """Return (key, rank, match_type), preferring the accepted usage for synonyms."""
    for container in ("acceptedUsage", "usage"):
        u = resp.get(container)
        if isinstance(u, dict) and u.get("key") is not None:
            diag = resp.get("diagnostics", {})
            return str(u["key"]), u.get("rank"), diag.get("matchType")
    # Flat fallback, in case the response isn't nested as expected.
    for flat in ("acceptedUsageKey", "usageKey", "key"):
        if resp.get(flat) is not None:
            return str(resp[flat]), resp.get("rank"), resp.get("matchType")
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description="Resolve names to GBIF CoL taxon keys.")
    ap.add_argument("names", nargs="+",
                    help="One or more scientific names (quote them).")
    ap.add_argument("--checklist", default=COL_XR, help="Checklist key to match against.")
    args = ap.parse_args()

    keys = []
    for name in args.names:
        key, rank, match_type = pick_key(match(name, args.checklist))
        keys.append(key)
        print(f"{name:24} key={key}  rank={rank}  match={match_type}")

    print()
    print("taxon_keys: [" + ", ".join(f'"{k}"' for k in keys) + "]   # with col_backbone: true")


if __name__ == "__main__":
    main()
