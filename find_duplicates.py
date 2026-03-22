import argparse
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from utils import format_size, HashCache

console = Console()


def find_duplicates(folder, cache):
    """Return dict mapping SHA-256 hash -> list of duplicate Paths."""
    size_groups = defaultdict(list)
    total_files = 0

    console.print(f"[bold]Scanning:[/bold] {folder}\n")

    for entry in folder.rglob("*"):
        if entry.is_file():
            try:
                size_groups[entry.stat().st_size].append(entry)
                total_files += 1
            except (PermissionError, OSError):
                pass

    candidates = [files for files in size_groups.values() if len(files) > 1]
    candidate_count = sum(len(f) for f in candidates)

    console.print(f"Found [cyan]{total_files}[/cyan] files. "
                  f"Hashing [cyan]{candidate_count}[/cyan] candidates...\n")

    hash_groups = defaultdict(list)

    with Progress(console=console) as progress:
        task = progress.add_task("Hashing files", total=candidate_count)
        for files in candidates:
            for path in files:
                digest = cache.get(path)
                if digest:
                    hash_groups[digest].append(path)
                progress.advance(task)

    return {h: paths for h, paths in hash_groups.items() if len(paths) > 1}


def main():
    parser = argparse.ArgumentParser(description="Find duplicate files in a directory.")
    parser.add_argument(
        "directory",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="Directory to scan (default: ~/Downloads)",
    )
    args = parser.parse_args()

    scan_dir = Path(args.directory).resolve()
    if not scan_dir.exists():
        console.print(f"[red]Error:[/red] folder not found: {scan_dir}")
        return

    cache = HashCache(scan_dir)
    try:
        duplicates = find_duplicates(scan_dir, cache)
    finally:
        cache.close()

    if not duplicates:
        console.print("\n[green]No duplicate files found.[/green]")
        return

    total_wasted = 0

    table = Table(title="Duplicate Files", show_lines=True)
    table.add_column("Group", justify="right", style="bold")
    table.add_column("Size", style="cyan")
    table.add_column("Copies", justify="right")
    table.add_column("Wasted", style="red")
    table.add_column("Files")

    for i, (digest, paths) in enumerate(duplicates.items(), 1):
        size = paths[0].stat().st_size
        wasted = size * (len(paths) - 1)
        total_wasted += wasted

        sorted_paths = sorted(paths, key=lambda p: len(str(p)))
        file_list = ""
        for j, path in enumerate(sorted_paths):
            marker = "[green]KEEP?[/green]" if j == 0 else "[red]DUPE?[/red]"
            file_list += f"{marker}  {path}\n"

        table.add_row(
            str(i),
            format_size(size),
            str(len(paths)),
            format_size(wasted),
            file_list.strip(),
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Total reclaimable space:[/bold] [red]{format_size(total_wasted)}[/red]")
    console.print("\n[dim]Nothing was deleted. Review the list above and remove duplicates manually.[/dim]")


if __name__ == "__main__":
    main()
