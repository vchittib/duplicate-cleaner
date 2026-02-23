import os
import hashlib
from collections import defaultdict
from pathlib import Path

SCAN_DIR = Path(r"C:\Users\vishu\Downloads")


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
    # Step 1: group files by size (fast pre-filter — different sizes can't be duplicates)
    size_groups = defaultdict(list)
    total_files = 0

    print(f"Scanning: {folder}\n")

    for entry in folder.rglob("*"):
        if entry.is_file():
            try:
                size_groups[entry.stat().st_size].append(entry)
                total_files += 1
            except (PermissionError, OSError):
                pass

    print(f"Found {total_files} files. Checking for duplicates...\n")

    # Step 2: hash only files that share a size
    hash_groups = defaultdict(list)
    candidates = [files for files in size_groups.values() if len(files) > 1]
    candidate_count = sum(len(f) for f in candidates)

    checked = 0
    for files in candidates:
        for path in files:
            digest = hash_file(path)
            if digest:
                hash_groups[digest].append(path)
            checked += 1
            print(f"\r  Hashing files: {checked}/{candidate_count}", end="", flush=True)

    if candidate_count:
        print()  # newline after progress

    # Step 3: keep only groups with more than one file
    duplicates = {h: paths for h, paths in hash_groups.items() if len(paths) > 1}
    return duplicates


def main():
    if not SCAN_DIR.exists():
        print(f"Error: folder not found: {SCAN_DIR}")
        return

    duplicates = find_duplicates(SCAN_DIR)

    if not duplicates:
        print("\nNo duplicate files found.")
        return

    total_groups = len(duplicates)
    total_wasted = 0

    print(f"\n{'='*60}")
    print(f"  Found {total_groups} group{'s' if total_groups != 1 else ''} of duplicate files")
    print(f"{'='*60}\n")

    for i, (digest, paths) in enumerate(duplicates.items(), 1):
        size = paths[0].stat().st_size
        wasted = size * (len(paths) - 1)
        total_wasted += wasted

        print(f"Group {i}  —  {format_size(size)} each  "
              f"({len(paths)} copies, {format_size(wasted)} wasted)")
        print(f"  Hash: {digest[:16]}...")

        # Sort: shortest path first (likely the "original")
        for j, path in enumerate(sorted(paths, key=lambda p: len(str(p)))):
            marker = "  KEEP?  " if j == 0 else "  DUPE?  "
            print(f"{marker} {path}")
        print()

    print(f"{'='*60}")
    print(f"  Total reclaimable space: {format_size(total_wasted)}")
    print(f"{'='*60}")
    print("\nNothing was deleted. Review the list above and remove duplicates manually.")


if __name__ == "__main__":
    main()
