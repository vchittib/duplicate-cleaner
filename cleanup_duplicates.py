import os
import re
import hashlib
from collections import defaultdict
from pathlib import Path
from send2trash import send2trash

SCAN_DIR = Path(r"C:\Users\vishu\Downloads")

# Matches filenames ending with (1), (2), (3) etc. before the extension
NUMBERED_RE = re.compile(r'^(.*)\s\(\d+\)(\.[^.]+)?$')


def format_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def hash_file(path, chunk_size=65536):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def find_duplicates(folder):
    size_groups = defaultdict(list)
    for entry in folder.rglob("*"):
        if entry.is_file():
            try:
                size_groups[entry.stat().st_size].append(entry)
            except (PermissionError, OSError):
                pass

    hash_groups = defaultdict(list)
    candidates = [f for f in size_groups.values() if len(f) > 1]
    total = sum(len(f) for f in candidates)
    checked = 0

    for files in candidates:
        for path in files:
            digest = hash_file(path)
            if digest:
                hash_groups[digest].append(path)
            checked += 1
            print(f"\r  Scanning: {checked}/{total}", end="", flush=True)

    if total:
        print()

    return {h: p for h, p in hash_groups.items() if len(p) > 1}


def pick_numbered_dupes(paths):
    """
    Within a duplicate group, return files that:
      - match the '(n)' pattern, AND
      - have a counterpart without the number in the same group
    """
    to_delete = []
    path_strings = {str(p) for p in paths}

    for path in paths:
        stem = path.stem
        suffix = path.suffix
        m = NUMBERED_RE.match(stem + suffix)
        if not m:
            continue
        # Build what the "original" filename would look like
        base = m.group(1)
        ext = m.group(2) or ""
        original = path.parent / (base + ext)
        if str(original) in path_strings:
            to_delete.append(path)

    return to_delete


def main():
    print(f"Scanning {SCAN_DIR} for duplicates...\n")
    duplicates = find_duplicates(SCAN_DIR)

    if not duplicates:
        print("No duplicates found.")
        return

    # Collect all files safe to delete
    to_delete = []
    for paths in duplicates.values():
        to_delete.extend(pick_numbered_dupes(paths))

    if not to_delete:
        print("No numbered duplicates found to clean up.")
        return

    total_size = sum(p.stat().st_size for p in to_delete if p.exists())

    print(f"Found {len(to_delete)} numbered duplicate(s) to move to Recycle Bin")
    print(f"Total space to reclaim: {format_size(total_size)}\n")
    print("Files to be recycled:")
    for p in sorted(to_delete):
        print(f"  {p}")

    print(f"\n{'-'*60}")
    confirm = input(f"Move these {len(to_delete)} files to the Recycle Bin? [yes/no]: ").strip().lower()

    if confirm != "yes":
        print("Aborted. Nothing was deleted.")
        return

    success, failed = 0, []
    for path in to_delete:
        try:
            send2trash(str(path))
            print(f"  Recycled: {path.name}")
            success += 1
        except Exception as e:
            print(f"  FAILED:   {path.name} — {e}")
            failed.append(path)

    print(f"\nDone. {success} file(s) moved to Recycle Bin ({format_size(total_size)} freed).")
    if failed:
        print(f"{len(failed)} file(s) could not be deleted — check permissions.")


if __name__ == "__main__":
    main()
