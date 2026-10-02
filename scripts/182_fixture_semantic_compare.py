#!/usr/bin/env python3
"""Semantic diff for frappe fixture JSONs / DocType JSONs.

Compares two directory trees of exported fixtures while ignoring volatile
metadata (modified, modified_by, creation, owner) and JSON ordering, so a
routine re-export only flags REAL content changes.

Usage:
    python3 182_fixture_semantic_compare.py <old_dir> <new_dir> [rel_paths...]

If no rel_paths are given, all *.json files present in BOTH trees are compared.
Exit codes: 0 = semantically identical, 1 = differences found, 2 = usage/IO error.
"""
import json
import os
import sys

META = {"modified", "modified_by", "creation", "owner"}


def canon(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    out = {}
    for e in data:
        e = {k: v for k, v in e.items() if k not in META}
        key = e.get("name") or json.dumps(e, sort_keys=True)[:80]
        out[key] = e
    return out


def rel_jsons(root):
    out = set()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fn:
            if f.endswith(".json"):
                out.add(os.path.relpath(os.path.join(dp, f), root))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    old_root, new_root = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    rels = sys.argv[3:] or sorted(rel_jsons(old_root) & rel_jsons(new_root))

    diffs = 0
    for rel in rels:
        old_p, new_p = os.path.join(old_root, rel), os.path.join(new_root, rel)
        if not (os.path.exists(old_p) and os.path.exists(new_p)):
            print("MISSING:", rel, "(old)" if not os.path.exists(old_p) else "(new)")
            diffs += 1
            continue
        try:
            old, new = canon(old_p), canon(new_p)
        except Exception as ex:
            print("ERROR parsing", rel, ":", ex)
            diffs += 1
            continue
        problems = []
        only_old = set(old) - set(new)
        only_new = set(new) - set(old)
        if only_old:
            problems.append("only in OLD: " + ", ".join(sorted(only_old)[:10]))
        if only_new:
            problems.append("only in NEW: " + ", ".join(sorted(only_new)[:10]))
        for k in sorted(set(old) & set(new)):
            if old[k] != new[k]:
                fields = {
                    f: (old[k].get(f), new[k].get(f))
                    for f in set(old[k]) | set(new[k])
                    if old[k].get(f) != new[k].get(f)
                }
                problems.append("CHANGED " + k + ": " + json.dumps(fields, default=str)[:400])
        if problems:
            diffs += 1
            print("=====", rel)
            for p in problems[:25]:
                print("  ", p)
            if len(problems) > 25:
                print("   ...and", len(problems) - 25, "more")
        else:
            print("OK (identical):", rel)

    print("RESULT:", "DIFFERENCES FOUND" if diffs else "ALL IDENTICAL")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
