#!/usr/bin/env python3
"""Re-verify every optimisation record proposed in PERF-ADDITIONS.txt.

PERF-ADDITIONS.txt holds two pipe-separated blocks:

  * the merge-ready records - the same 11 fields as the five category files
                              (kind|side|source|slug|mr_id|cf_id|client|
                               server|version|packs|display name)
  * the evidence block      - the same 10 fields as MRPACK-MANIFEST.txt
                              (kind|side|slug|mr_id|version_id|
                               version_number|file name|size|sha1|url)

This script reads both and checks, against the live Modrinth API:

  1. the slug is not already used by a record in 0*-*.txt (no duplicates)
  2. project id, slug and the client_side / server_side flags still match the
     API - i.e. the record would still be filed on the right side
  3. the pinned version_number really has a Forge 1.20.1 file, and that file's
     version_id, file name, size and sha1 match the evidence block
  4. the CDN url answers HTTP 200 with the recorded size
  5. every required dependency of every record is either already in 0*-*.txt
     or proposed in PERF-ADDITIONS.txt (catches a missing library record)
  6. the tier counts the merge would produce

Usage:  python3 tools/check_perf_additions.py       (run from the repo root)
Exit:   0 = all records verified, 1 = drift, missing dependency or bad record
"""
import concurrent.futures
import glob
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.modrinth.com/v2"
UA = {"User-Agent": "rune-modlist-audit/1.0"}
GAME = '["1.20.1"]'
LOADERS = '["forge"]'
TIERS = ("S", "N", "L", "M", "H")
PROPOSAL = "PERF-ADDITIONS.txt"
EVIDENCE = {}


def request(url, method="GET"):
    """urlopen with a small backoff - the Modrinth API rate-limits bursts."""
    last = None
    for attempt in range(5):
        req = urllib.request.Request(url, headers=UA, method=method)
        try:
            return urllib.request.urlopen(req, timeout=40)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
        except urllib.error.URLError as exc:
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise last


def get(url):
    return json.load(request(url))


def head(url):
    resp = request(url, method="HEAD")
    return resp.status, int(resp.headers.get("Content-Length") or -1)


def load_shipped():
    """slug -> mr_id and mr_id -> slug for everything already in 01-05."""
    slugs, ids = {}, {}
    for path in sorted(glob.glob("0*-*.txt")):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) != 11:
                    continue
                slugs[parts[3]] = parts[4]
                ids[parts[4]] = parts[3]
    return slugs, ids


def load_proposal():
    global EVIDENCE
    records, evidence = [], {}
    group = "?"
    with open(PROPOSAL) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                if "P1" in line and "RECORDS" in line:
                    group = "P1"
                elif "P2" in line and "RECORDS" in line:
                    group = "P2"
                continue
            if not line:
                continue
            parts = line.split("|")
            if len(parts) == 11:
                records.append((group, parts))
            elif len(parts) == 10:
                evidence[parts[2]] = parts
    EVIDENCE = evidence
    return records, evidence


def verify(item):
    group, rec = item
    kind, side, source, slug, mr_id, cf_id, cl, sv, ver, packs, name = rec

    if kind != "mod" or source != "modrinth":
        return slug, False, ["kind/source must be mod/modrinth"], 0, [], group
    if not mr_id:
        return slug, False, ["blank mr_id - cannot be packed"], 0, [], group
    if side not in ("BOTH", "SERVER", "CLIENT"):
        return slug, False, ["bad side %r" % side], 0, [], group
    bad = [t for t in packs.split(",") if t not in TIERS]
    if bad:
        return slug, False, ["bad packs token(s) %s" % ",".join(bad)], 0, [], group

    notes, ok = [], True
    try:
        project = get("%s/project/%s" % (API, mr_id))
    except Exception as exc:  # noqa: BLE001 - report, do not traceback
        return slug, False, ["project lookup failed: %s" % exc], 0, [], group
    if project["id"] != mr_id:
        ok = False
        notes.append("mr_id resolves to %s" % project["id"])
    if project["slug"] != slug:
        ok = False
        notes.append("slug is %r on Modrinth" % project["slug"])
    if (project["client_side"], project["server_side"]) != (cl, sv):
        ok = False
        notes.append(
            "side flags drifted: API %s/%s, record %s/%s"
            % (project["client_side"], project["server_side"], cl, sv)
        )

    url = "%s/project/%s/version?loaders=%s&game_versions=%s" % (
        API,
        mr_id,
        urllib.parse.quote(LOADERS),
        urllib.parse.quote(GAME),
    )
    try:
        versions = get(url)
    except Exception as exc:  # noqa: BLE001
        return slug, False, notes + ["version lookup failed: %s" % exc], 0, [], group
    pinned = [v for v in versions if v["version_number"] == ver]
    if not pinned:
        newest = versions[0]["version_number"] if versions else "none"
        return slug, False, notes + ["pinned %s missing (newest %s)" % (ver, newest)], 0, [], group
    version = pinned[0]
    if not version["files"]:
        return slug, False, notes + ["version %s has no file" % ver], 0, [], group
    fil = version["files"][0]

    ev = EVIDENCE.get(slug)
    if not ev:
        ok = False
        notes.append("no evidence line")
    else:
        e_side, _e_slug, e_id, e_vid, e_ver, e_fn, e_size, e_sha1, e_url = ev[1:]
        checks = (
            ("side", e_side, side),
            ("mr_id", e_id, mr_id),
            ("version_id", e_vid, version["id"]),
            ("version_number", e_ver, ver),
            ("file name", e_fn, fil["filename"]),
            ("size", e_size, str(fil["size"])),
            ("sha1", e_sha1, fil["hashes"].get("sha1", "")),
            ("url", e_url, fil["url"]),
        )
        for label, recorded, live in checks:
            if recorded != live:
                ok = False
                notes.append("%s drift: recorded %s, live %s" % (label, recorded, live))

    try:
        status, length = head(fil["url"])
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append("HEAD failed: %s" % exc)
    else:
        if status != 200:
            ok = False
            notes.append("CDN answered HTTP %s" % status)
        if length not in (-1, fil["size"]):
            ok = False
            notes.append("CDN Content-Length %s != %s" % (length, fil["size"]))

    deps = [
        d["project_id"]
        for d in version.get("dependencies", [])
        if d.get("dependency_type") == "required" and d.get("project_id")
    ]
    return slug, ok, notes, fil["size"], deps, group


def shipped_tier_counts():
    counts = {t: 0 for t in TIERS}
    for path in sorted(glob.glob("0*-*.txt")):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) != 11:
                    continue
                for t in parts[9].split(","):
                    counts[t] = counts.get(t, 0) + 1
    return counts


def main():
    shipped_slugs, shipped_ids = load_shipped()
    try:
        records, evidence = load_proposal()
    except OSError as exc:
        print("%s: %s" % (PROPOSAL, exc))
        return 1
    if not records:
        print("%s: no records found" % PROPOSAL)
        return 1

    proposed_ids = {rec[4] for _, rec in records}
    dupes = [rec[3] for _, rec in records if rec[3] in shipped_slugs]
    seen = set()
    for _, rec in records:
        if rec[3] in seen:
            dupes.append(rec[3] + " (twice in this file)")
        seen.add(rec[3])

    print("records: %d proposed | evidence lines: %d" % (len(records), len(evidence)))
    failures, missing_deps = [], []
    counts = {t: 0 for t in TIERS}
    groups = {"P1": 0, "P2": 0}
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for slug, ok, notes, size, deps, group in pool.map(verify, records):
            groups[group] = groups.get(group, 0) + 1
            rec = next(r for _, r in records if r[3] == slug)
            for t in rec[9].split(","):
                counts[t] += 1
            for dep in deps:
                if dep not in shipped_ids and dep not in proposed_ids:
                    missing_deps.append(
                        "%s needs %s (not in 01-05, not proposed)" % (slug, dep)
                    )
            if ok:
                print("  OK   %-28s %-9s %-28s %7d B" % (slug, rec[4], rec[8], size))
            else:
                print("  FAIL %-28s %s" % (slug, "; ".join(notes)))
                failures.append(slug)

    for slug in dupes:
        print("  FAIL duplicate slug already shipped: %s" % slug)
    for line in missing_deps:
        print("  FAIL dependency %s" % line)

    shipped = shipped_tier_counts()
    print("\nby group: " + ", ".join(
        "%s %d" % (k, v) for k, v in sorted(groups.items()) if v
    ))
    print("tier   now  ->  merged")
    for t in TIERS:
        print("  %s   %4d  ->  %4d" % (t, shipped[t], shipped[t] + counts[t]))

    bad = len(failures) + len(dupes) + len(missing_deps)
    print(
        "\n%s %d/%d records, %d duplicate slug(s), %d missing dependency(ies)"
        % (
            "FAIL" if bad else "PASS",
            len(records) - len(failures),
            len(records),
            len(dupes),
            len(missing_deps),
        )
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
