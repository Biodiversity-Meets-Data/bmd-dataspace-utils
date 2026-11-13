#!/usr/bin/env python3
"""
Resolve names to GBIF COL taxon keys and verify they actually have occurrences.

Same resolution as resolve_keys.py (v2 match against the Catalogue of Life
Extended Release), plus an occurrence count per key so a zero-occurrence key
can never slip into a recipe unnoticed.
"""

import argparse
import json
import urllib.parse
import urllib.request

COL_XR = "7ddf754f-d193-4cc9-b351-99906754a03b"
MATCH_URL = "https://api.gbif.org/v2/species/match"
SEARCH_URL = "https://api.gbif.org/v1/occurrence/search"

DEFAULT_NAMES = [
    "Canis lupus",
    "Cervus elaphus",
    "Sus scrofa",
    "Capreolus capreolus",
]


def get(url, params):
    with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=30) as r:
        return json.load(r)


def pick_key(resp):
    for container in ("acceptedUsage", "usage"):
        u = resp.get(container)
        if isinstance(u, dict) and u.get("key") is not None:
            diag = resp.get("diagnostics", {})
            return str(u["key"]), u.get("rank"), diag.get("matchType")
    for flat in ("acceptedUsageKey", "usageKey", "key"):
        if resp.get(flat) is not None:
            return str(resp[flat]), resp.get("rank"), resp.get("matchType")
    return None, None, None


def occurrence_count(key, checklist, country):
    params = {
        "taxonKey": key,
        "checklistKey": checklist,
        "hasCoordinate": "true",
        "limit": 0,
    }
    if country:
        params["country"] = country
    return get(SEARCH_URL, params)["count"]


def main():
    ap = argparse.ArgumentParser(description="Resolve and verify GBIF COL taxon keys.")
    ap.add_argument("names", nargs="*", default=DEFAULT_NAMES,
                    help="Scientific names (default: the Veluwe predator-prey set).")
    ap.add_argument("--country", default="NL",
                    help="ISO country code to count within, or empty for worldwide.")
    ap.add_argument("--checklist", default=COL_XR, help="Checklist key to match against.")
    args = ap.parse_args()

    keys = []
    for name in args.names:
        key, rank, match_type = pick_key(get(MATCH_URL, {"scientificName": name, "checklistKey": args.checklist}))
        keys.append(key)
        count = occurrence_count(key, args.checklist, args.country) if key else "-"
        flag = "  <-- no occurrences" if count == 0 else ""
        print(f"{name:24} key={key}  rank={rank}  match={match_type}  count={count}{flag}")

    print()
    print("taxon_keys: [" + ", ".join(f'"{k}"' for k in keys) + "]   # with col_backbone: true")


if __name__ == "__main__":
    main()