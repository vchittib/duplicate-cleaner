# Productivity Agent — Design Suggestions

Building on the existing duplicate-cleaner foundation, here are practical directions for a productivity agent that helps users manage their file system and reclaim time.

---

## 1. Scheduled & Watched Folder Cleanup

**What it does:** Continuously monitors directories (e.g., Downloads, Desktop) and automatically flags or cleans duplicates on a schedule.

**Key ideas:**
- Use `watchdog` to detect new files and immediately check against known hashes
- Maintain a persistent SQLite database of file hashes so rescans are incremental (only hash new/changed files)
- Support cron-like scheduling or run as a background daemon
- Send desktop notifications (via `plyer` or `notify-py`) when duplicates are found

**Why it helps:** Users don't have to remember to run the tool — the agent does it for them.

---

## 2. Smart File Organizer

**What it does:** Goes beyond duplicate detection — sorts files into folders by type, date, or project.

**Key ideas:**
- Rule engine: define rules like "move `.pdf` files older than 30 days to `~/Archive/PDFs`"
- YAML/JSON config for user-defined rules so it's flexible without code changes
- Dry-run mode that shows what *would* happen before moving anything
- Undo log: record every action in a JSON ledger so moves can be reversed

```yaml
# Example rules.yaml
rules:
  - match: "*.pdf"
    older_than_days: 30
    action: move
    destination: ~/Archive/PDFs
  - match: "*.png|*.jpg"
    larger_than_mb: 5
    action: compress
    destination: ~/Archive/Images
```

---

## 3. Disk Space Advisor

**What it does:** Analyzes disk usage and gives actionable recommendations.

**Key ideas:**
- Identify the top N largest files and directories
- Flag large files that haven't been accessed in X days
- Detect common space wasters: node_modules, .git bloat, cache dirs, old logs
- Generate a prioritized report: "Delete these 5 things to free 12 GB"

---

## 4. Interactive CLI Agent (Conversational)

**What it does:** Wrap the tools above in a conversational CLI that understands natural-language-ish commands.

**Key ideas:**
- Use `argparse` subcommands or a simple REPL loop
- Commands like: `scan ~/Downloads`, `clean duplicates`, `organize by type`, `show space report`
- Confirm before destructive actions (you already do this well in `cleanup_duplicates.py`)
- Colorized output with `rich` for better readability

```
> scan ~/Downloads
Found 1,247 files. 38 duplicate groups detected (420 MB reclaimable).

> clean duplicates --numbered-only
12 numbered duplicates found. Move to trash? [yes/no]:

> organize ~/Downloads --dry-run
Would move 23 PDFs to ~/Documents/PDFs
Would move 8 installers to ~/Archive/Installers
```

---

## 5. Cross-Platform Improvements

Your current scripts hardcode `C:\Users\vishu\Downloads`. Suggested refactors:

- Accept the target directory as a CLI argument with a sensible default (`~/Downloads`)
- Use `platformdirs` or `Path.home()` for cross-platform paths
- Replace `send2trash` usage with a fallback for Linux (`trash-cli` or manual `~/.local/share/Trash`)

---

## 6. Suggested Architecture

```
duplicate-cleaner/
├── agent/
│   ├── __init__.py
│   ├── cli.py              # REPL / argparse entry point
│   ├── scanner.py           # Refactored find_duplicates (reusable)
│   ├── cleaner.py           # Refactored cleanup logic
│   ├── organizer.py         # Rule-based file organizer
│   ├── advisor.py           # Disk space analysis
│   ├── watcher.py           # watchdog-based folder monitor
│   └── db.py                # SQLite hash cache
├── config/
│   └── rules.yaml           # User-defined organization rules
├── tests/
│   ├── test_scanner.py
│   ├── test_cleaner.py
│   └── test_organizer.py
├── find_duplicates.py        # Original script (kept for compat)
├── cleanup_duplicates.py     # Original script (kept for compat)
└── pyproject.toml
```

---

## 7. Quick Wins to Start

1. **Refactor shared code** — `hash_file` and `format_size` are duplicated across both scripts. Extract them into a shared module.
2. **Make scan directory configurable** — Accept it as a CLI arg instead of hardcoding.
3. **Add a hash cache** — Store hashes in a small SQLite DB so repeated scans skip unchanged files.
4. **Add `rich` output** — Progress bars, colored tables, and panels make the tool feel polished.

These four changes are small, high-impact, and set up the foundation for everything else.
