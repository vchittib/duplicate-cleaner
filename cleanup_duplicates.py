import re
import argparse
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from utils import format_size, HashCache

console = Console()

# Matches filenames ending with (1), (2), (3) etc. before the extension
NUMBERED_RE = re.compile(r'^(.*)\s\(\d+\)(\.[^.]+)?$')


def find_duplicates(folder, cache):
    """Return dict mapping SHA-256 hash -> list of duplicate Paths."""
    size_groups = defaultdict(list)
    for entry in folder.rglob("*"):
        if entry.is_file():
            try:
                size_groups[entry.stat().st_size].append(entry)
            except (PermissionError, OSError):
                pass

    candidates = [f for f in size_groups.values() if len(f) > 1]
    total = sum(len(f) for f in candidates)

    hash_groups = defaultdict(list)

    with Progress(console=console) as progress:
        task = progress.add_task("Scanning files", total=total)
        for files in candidates:
            for path in files:
                digest = cache.get(path)
                if digest:
                    hash_groups[digest].append(path)
                progress.advance(task)

    return {h: p for h, p in hash_groups.items() if len(p) > 1}


def pick_numbered_dupes(paths):
    """Within a duplicate group, return files that match the '(n)' pattern
    and have a counterpart without the number in the same group."""
    to_delete = []
    path_strings = {str(p) for p in paths}

    for path in paths:
        stem = path.stem
        suffix = path.suffix
        m = NUMBERED_RE.match(stem + suffix)
        if not m:
            continue
        base = m.group(1)
        ext = m.group(2) or ""
        original = path.parent / (base + ext)
        if str(original) in path_strings:
            to_delete.append(path)

    return to_delete


def main():
    parser = argparse.ArgumentParser(description="Clean up numbered duplicate files.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="Directory to scan (default: ~/Downloads)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting.",
    )
    args = parser.parse_args()

    scan_dir = Path(args.directory).resolve()
    if not scan_dir.exists():
        console.print(f"[red]Error:[/red] folder not found: {scan_dir}")
        return

    console.print(f"[bold]Scanning[/bold] {scan_dir} for duplicates...\n")

    cache = HashCache(scan_dir)
    try:
        duplicates = find_duplicates(scan_dir, cache)
    finally:
        cache.close()

    if not duplicates:
        console.print("[green]No duplicates found.[/green]")
        return

    to_delete = []
    for paths in duplicates.values():
        to_delete.extend(pick_numbered_dupes(paths))

    if not to_delete:
        console.print("[green]No numbered duplicates found to clean up.[/green]")
        return

    total_size = sum(p.stat().st_size for p in to_delete if p.exists())

    table = Table(title="Files to Remove")
    table.add_column("File", style="red")
    table.add_column("Size", justify="right", style="cyan")
    for p in sorted(to_delete):
        table.add_row(str(p), format_size(p.stat().st_size))

    console.print(table)
    console.print(f"\n[bold]{len(to_delete)}[/bold] numbered duplicate(s), "
                  f"[bold cyan]{format_size(total_size)}[/bold cyan] reclaimable\n")

    if args.dry_run:
        console.print("[yellow]Dry run — nothing was deleted.[/yellow]")
        return

    confirm = console.input(f"Move these {len(to_delete)} files to trash? [yellow]\\[yes/no][/yellow]: ").strip().lower()
    if confirm != "yes":
        console.print("[dim]Aborted. Nothing was deleted.[/dim]")
        return

    try:
        from send2trash import send2trash
    except ImportError:
        console.print("[red]Error:[/red] send2trash is not installed. Run: pip install send2trash")
        return

    success, failed = 0, []
    for path in to_delete:
        try:
            send2trash(str(path))
            console.print(f"  [green]Recycled:[/green] {path.name}")
            success += 1
        except Exception as e:
            console.print(f"  [red]FAILED:[/red]   {path.name} — {e}")
            failed.append(path)

    console.print(f"\n[bold green]Done.[/bold green] {success} file(s) moved to trash "
                  f"({format_size(total_size)} freed).")
    if failed:
        console.print(f"[red]{len(failed)} file(s) could not be deleted — check permissions.[/red]")


if __name__ == "__main__":
    main()
