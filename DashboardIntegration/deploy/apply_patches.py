#!/usr/bin/env python3
"""Apply the SW-7 integration to a COPY of the dashboard.

  python3 apply_patches.py ~/Dashboard_sw7 [--source DIR] [--native-map]

Reads dashboard_patches.py (COPIES and PATCHES) from the source folder
(default: the folder this script is in, ~/sw7_integration on the Pi 5),
copies the integration modules into the target and makes the text edits.
sw7_endpoints.py and sw7_live_only.py, if present in the source folder
and not already listed in COPIES, are copied to app/data/ (both are
imported from there: ..data.sw7_endpoints and .sw7_live_only).

Safety:
- refuses to touch ~/Dashboard (the team copy) or anything inside it;
- every patch anchor must occur exactly once at the moment it is applied;
  all edits are worked out in memory first and nothing is written unless
  every one of them matches, so a failed run leaves the target unchanged.

--native-map sets "map_display_provider" to "Native fallback" under
"global" in app/asis/data/user_prefs.json (the web map crashes on the
Pi 5 display, PI5_MAP_CRASH.md).

Prints what it did, with counts. Exit 0 on success, 1 on any failure.
Standard library only.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys

PREFS = os.path.join("app", "asis", "data", "user_prefs.json")
EXTRA_MODULES = (("sw7_endpoints.py", "app/data/sw7_endpoints.py"),
                 ("sw7_live_only.py", "app/data/sw7_live_only.py"))


def fail(msg):
    print("ERROR: %s" % msg, file=sys.stderr)
    sys.exit(1)


def is_inside(path, parent):
    path, parent = os.path.realpath(path), os.path.realpath(parent)
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def load_patches(source):
    path = os.path.join(source, "dashboard_patches.py")
    if not os.path.isfile(path):
        fail("dashboard_patches.py not found in %s" % source)
    spec = importlib.util.spec_from_file_location("dashboard_patches", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(getattr(mod, "COPIES", ())), list(mod.PATCHES)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Apply the SW-7 integration to a copy of the dashboard")
    ap.add_argument("target", help="the dashboard COPY to patch, e.g. ~/Dashboard_sw7")
    ap.add_argument("--source", default=os.path.dirname(os.path.abspath(__file__)),
                    help="folder with dashboard_patches.py and the integration modules")
    ap.add_argument("--native-map", action="store_true",
                    help='set map_display_provider to "Native fallback" in the copy\'s user_prefs.json')
    ap.add_argument("--team-dir", default="~/Dashboard",
                    help="the team copy that must never be modified (default ~/Dashboard)")
    a = ap.parse_args(argv)

    target = os.path.abspath(os.path.expanduser(a.target))
    source = os.path.abspath(os.path.expanduser(a.source))
    team = os.path.expanduser(a.team_dir)

    if os.path.exists(team) and is_inside(target, team):
        fail("refusing to modify %s: that is the team copy (%s). Patch a copy instead." % (target, team))
    if not os.path.isfile(os.path.join(target, "main.py")) or not os.path.isdir(os.path.join(target, "app")):
        fail("%s does not look like a dashboard copy (no main.py or app/)" % target)

    copies, patches = load_patches(source)
    for extra, dst in EXTRA_MODULES:
        if (os.path.isfile(os.path.join(source, extra))
                and not any(src == extra for src, _ in copies)):
            copies.append((extra, dst))

    # 1. Check every copy source exists.
    for src, dst in copies:
        if not os.path.isfile(os.path.join(source, src)):
            fail("integration file %s missing from %s" % (src, source))

    # 2. Work out every text edit in memory, in order.
    texts = {}
    per_file = {}
    for i, (rel, old, new) in enumerate(patches, 1):
        path = os.path.join(target, rel)
        if rel not in texts:
            if not os.path.isfile(path):
                fail("patch %d: %s not found in the target" % (i, rel))
            with open(path, "r", encoding="utf-8", newline="") as f:
                texts[rel] = f.read()
        if "\r\n" in texts[rel]:
            # Keep the file's own line endings (a copy checked out on
            # Windows has CRLF; the anchors are written with LF).
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        n = texts[rel].count(old)
        if n != 1:
            first = old.strip().splitlines()[0] if old.strip() else repr(old)
            fail("patch %d (%s): anchor found %d times, must be exactly 1. Anchor starts: %r%s" % (
                i, rel, n, first[:90],
                " (already patched? rebuild the copy from ~/Dashboard first)" if n == 0 and new in texts[rel] else ""))
        texts[rel] = texts[rel].replace(old, new)
        per_file[rel] = per_file.get(rel, 0) + 1

    prefs_path = os.path.join(target, PREFS)
    prefs = None
    if a.native_map:
        try:
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except (OSError, ValueError) as e:
            fail("cannot read %s: %s" % (prefs_path, e))
        if not isinstance(prefs.get("global"), dict):
            fail('%s has no "global" object' % prefs_path)

    # 3. Everything matched: write.
    for src, dst in copies:
        d = os.path.join(target, dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(os.path.join(source, src), d)
        print("copied  %-26s -> %s" % (src, dst))
    for rel, text in texts.items():
        with open(os.path.join(target, rel), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("patched %-40s %d edit(s)" % (rel, per_file[rel]))
    if prefs is not None:
        before = prefs["global"].get("map_display_provider")
        prefs["global"]["map_display_provider"] = "Native fallback"
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
            f.write("\n")
        print('prefs   global.map_display_provider: %r -> "Native fallback"' % before)

    print("OK: %d file(s) copied, %d edit(s) in %d file(s), target %s" % (
        len(copies), sum(per_file.values()), len(per_file), target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
