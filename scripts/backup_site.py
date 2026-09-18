#!/usr/bin/env python3
"""Nightly backup of everything curators edit on the live site.

Downloads /admin/backup (a tar.gz of the Render persistent disk: videos, FAQ,
glossary, museum pages, uploads, feedback) into a dated file under the backup
folder, verifies it opens, unpacks the newest copy into `latest/` so files are
easy to diff or restore one at a time, and prunes archives older than KEEP_DAYS.

Credentials come from a file, never from this script or the command line:

    ~/.config/submarinedocent/backup.env
        SITE=https://submarinedocent.org
        ADMIN_USERNAME=...
        ADMIN_PASSWORD=...
        BACKUP_DIR=~/Backups/submarinedocent      (optional)
        KEEP_DAYS=60                              (optional)

    chmod 600 ~/.config/submarinedocent/backup.env

Run by hand:   python3 scripts/backup_site.py
Run nightly:   see docs/Backups.md (launchd)
Exit code is non-zero on any failure so launchd logs it.
"""
import base64, datetime, os, sys, tarfile, urllib.error, urllib.request, shutil

ENV_PATH = os.path.expanduser("~/.config/submarinedocent/backup.env")


def load_env(path):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                # Allow KEY="value" or KEY='value', but only unwrap when the
                # quotes are a matching pair; a password may legitimately end
                # in a quote character.
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                    v = v[1:-1]
                env[k.strip()] = v
    except FileNotFoundError:
        sys.exit(f"Missing {path}. See the header of this script for its format.")
    for k in ("ADMIN_USERNAME", "ADMIN_PASSWORD"):
        if not env.get(k):
            sys.exit(f"{path} is missing {k}")
    env.setdefault("SITE", "https://submarinedocent.org")
    env.setdefault("BACKUP_DIR", "~/Backups/submarinedocent")
    env.setdefault("KEEP_DAYS", "60")
    return env


def main():
    env = load_env(ENV_PATH)
    site = env["SITE"].rstrip("/")
    backup_dir = os.path.expanduser(env["BACKUP_DIR"])
    keep_days = int(env["KEEP_DAYS"])
    os.makedirs(backup_dir, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    out = os.path.join(backup_dir, f"submarinedocent-{stamp}.tar.gz")
    tmp = out + ".part"

    auth = base64.b64encode(f"{env['ADMIN_USERNAME']}:{env['ADMIN_PASSWORD']}".encode()).decode()
    req = urllib.request.Request(site + "/admin/backup")
    req.add_header("Authorization", "Basic " + auth)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
            files = resp.headers.get("X-Backup-Files", "?")
    except urllib.error.HTTPError as e:
        sys.exit(f"Backup failed: HTTP {e.code} from {site}/admin/backup (wrong password? site down?)")
    except urllib.error.URLError as e:
        sys.exit(f"Backup failed: {e.reason}")

    # Verify before trusting it.
    try:
        with tarfile.open(tmp, "r:gz") as t:
            names = t.getnames()
            if "MANIFEST.json" not in names or not any(n.endswith("videos.jsonl") for n in names):
                raise tarfile.TarError("archive is missing expected files")
    except tarfile.TarError as e:
        os.remove(tmp)
        sys.exit(f"Backup failed: downloaded archive is not valid ({e})")
    os.replace(tmp, out)
    size_kb = os.path.getsize(out) // 1024
    print(f"saved {out}  ({size_kb} KB, {files} files)")

    # Unpack the newest copy so individual files are at hand.
    latest = os.path.join(backup_dir, "latest")
    if os.path.isdir(latest):
        shutil.rmtree(latest)
    with tarfile.open(out, "r:gz") as t:
        # The "data" filter (Python 3.12+) refuses paths that escape the target
        # directory; older Pythons don't have it, so check the members ourselves.
        for m in t.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/"):
                sys.exit(f"Backup failed: archive contains an unsafe path ({m.name})")
        try:
            t.extractall(latest, filter="data")
        except TypeError:
            t.extractall(latest)
    print(f"unpacked to {latest}")

    # Prune.
    cutoff = datetime.datetime.now() - datetime.timedelta(days=keep_days)
    removed = 0
    for name in os.listdir(backup_dir):
        if not (name.startswith("submarinedocent-") and name.endswith(".tar.gz")):
            continue
        p = os.path.join(backup_dir, name)
        if datetime.datetime.fromtimestamp(os.path.getmtime(p)) < cutoff:
            os.remove(p)
            removed += 1
    if removed:
        print(f"pruned {removed} archive(s) older than {keep_days} days")


if __name__ == "__main__":
    main()
