#!/usr/bin/env python3
"""
Utility scripts. Looks up GBIF usage keys for the wolf and ir prey.
Outputs a line with keys, to be pasted into the recipe. (Has already been done.)
"""

import sys
import urllib.parse
import urllib.request
import json

NAMES = [
    "Canis lupus",
    "Cervus elaphus",
    "Sus scrofa",
    "Capreolus capreolus",
]

MATCH_URL = "https://api.gbif.org/v1/species/match?strict=true&name="


def match(name):
    with urllib.request.urlopen(MATCH_URL + urllib.parse.quote(name), timeout=30) as r:
        return json.load(r)


def main():
    keys = []
    ok = True
    for name in NAMES:
        d = match(name)
        key = d.get("usageKey")
        rank = d.get("rank")
        status = d.get("status")
        matchtype = d.get("matchType")
        keys.append(key)

        flags = []
        if matchtype != "EXACT":
            flags.append(f"matchType={matchtype}")
        if status not in (None, "ACCEPTED"):
            flags.append(f"status={status}")
        if rank != "SPECIES":
            flags.append(f"rank={rank}")

        note = ("  <-- CHECK: " + ", ".join(flags)) if flags else ""
        print(f"{name:22} -> {key}  ({d.get('scientificName')}){note}")
        if flags:
            ok = False

    print()
    print("taxon_keys: [" + ", ".join(str(k) for k in keys) + "]")
    if not ok:
        print("\nOne or more matches need a look before you trust them.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
