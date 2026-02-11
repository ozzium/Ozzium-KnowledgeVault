#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, timezone

def find_vault_root(start_path: str) -> str:
    probe = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(probe, "codex.config.json")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    raise FileNotFoundError("Could not find codex.config.json in this folder or any parent folder.")
def load_config(vault_root: str):
    cfg_path = os.path.join(vault_root, "codex.config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_excluded(path_parts, exclude_folders):
    return any(part in exclude_folders for part in path_parts)

def scan_markdown_files(vault_root: str, cfg: dict):
    include_ext = set(cfg.get("include_extensions", [".md"]))
    exclude_folders = set(cfg.get("exclude_folders", []))

    files = []
    for root, dirs, filenames in os.walk(vault_root):
        rel_root = os.path.relpath(root, vault_root)
        parts = [] if rel_root == "." else rel_root.split(os.sep)

        if is_excluded(parts, exclude_folders):
            # Don't descend into excluded dirs
            dirs[:] = []
            continue

        # Prune excluded dirs from traversal
        dirs[:] = [d for d in dirs if d not in exclude_folders]

        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext.lower() not in include_ext:
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, vault_root)
            try:
                st = os.stat(full)
                files.append({
                    "rel": rel.replace("\\", "/"),
                    "mtime": st.st_mtime,
                    "size": st.st_size
                })
            except OSError:
                continue

    # Sort recent first
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files

def extract_tasks(vault_root: str, files: list, cfg: dict):
    max_tasks = int(cfg.get("max_tasks", 25))
    markers = cfg.get("task_markers", ["TODO", "FIXME"])
    checkbox_starts = cfg.get("task_checkbox_patterns", ["- [ ]", "* [ ]"])

    tasks = []

    for f in files:
        path = os.path.join(vault_root, f["rel"].replace("/", os.sep))
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for i, line in enumerate(fh, start=1):
                    s = line.strip()

                    # Checkbox tasks
                    if any(s.startswith(p) for p in checkbox_starts):
                        tasks.append((f["rel"], i, s))
                    else:
                        # Marker tasks (TODO/FIXME anywhere)
                        upper = s.upper()
                        if any(m in upper for m in markers):
                            tasks.append((f["rel"], i, s))

                    if len(tasks) >= max_tasks:
                        return tasks
        except OSError:
            continue

    return tasks
    
def md_link(path: str):
    # GitHub-friendly relative link
    return f"[{os.path.basename(path)}]({path})"

def group_by_top_folder(files):
    grouped = {}
    for f in files:
        parts = f["rel"].split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        grouped.setdefault(top, []).append(f)
    return grouped

def generate_section(cfg: dict, files: list, tasks: list):
    title = cfg.get("title", "Vault")
    max_recent = int(cfg.get("max_recent_files", 15))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    recent = files[:max_recent]
    grouped = group_by_top_folder(files)

    lines = []
    lines.append(f"### {title} — Codex Snapshot")
    lines.append("")
    lines.append(f"**Last generated:** {now}")
    lines.append("")

    # Recently updated
    lines.append("#### 🔥 Recently Updated")
    if not recent:
        lines.append("- (No markdown files found yet.)")
    else:
        for f in recent:
            ts = datetime.fromtimestamp(f["mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
            lines.append(f"- {md_link(f['rel'])} — {ts} · {f['size']} bytes")
    lines.append("")

    # Task harvesting
    lines.append("#### ✅ Open Tasks (harvested)")
    if not tasks:
        lines.append("- (No TODO/FIXME or unchecked tasks found.)")
    else:
        for rel, ln, text in tasks:
            link = f"[{os.path.basename(rel)}]({rel}#L{ln})"
            lines.append(f"- {link}: {text}")
    lines.append("")

    # Modules
    lines.append("#### 🗂️ Modules")
    for top in sorted(grouped.keys()):
        if top in ("tools", ".github", ".git", "__pycache__", "node_modules"):
            continue
        if top == "(root)":
            continue

        module_files = grouped[top][:8]
        lines.append(f"- **{top}/**")
        for mf in module_files:
            lines.append(f"  - {md_link(mf['rel'])}")
    lines.append("")

    # Quick start
    lines.append("#### 🧭 Quick Start")
    lines.append("- Add new notes anywhere under a module folder.")
    lines.append("- Commit/push → GitHub Action regenerates this Codex automatically.")
    lines.append("- Or run locally: `python tools/codex/build_codex.py`")
    lines.append("")

    return "\n".join(lines)

def replace_generated_section(readme_text: str, marker: str, new_block: str):
    # Replace everything from marker to end of file, or marker section only.
    # Simple + robust for a single generated section.
    idx = readme_text.find(marker)
    if idx == -1:
        # marker not found; append
        return readme_text.rstrip() + "\n\n" + marker + "\n\n" + new_block + "\n"

    # Keep content before marker, then marker + block
    prefix = readme_text[:idx].rstrip()
    return prefix + "\n\n" + marker + "\n\n" + new_block + "\n"

def main():
    # If user passed a vault root, use it; otherwise auto-detect
    if len(sys.argv) > 1:
        vault_root = os.path.abspath(sys.argv[1])
    else:
        vault_root = find_vault_root(os.getcwd())

    cfg = load_config(vault_root)
    files = scan_markdown_files(vault_root, cfg)
    tasks = extract_tasks(vault_root, files, cfg)

    print(f"[debug] files scanned: {len(files)} | tasks found: {len(tasks)}")

    marker = cfg.get("generated_section_marker", "## 🧠 Auto-Generated Codex")
    section = generate_section(cfg, files, tasks)

    readme_path = os.path.join(vault_root, "README.md")

    # Create README if it doesn't exist
    if not os.path.exists(readme_path):
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Ozzium Knowledge Vault\n\n" + marker + "\n\n(Placeholder)\n")

    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()

    updated = replace_generated_section(readme, marker, section)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)

    print("Codex updated in README.md")

if __name__ == "__main__":
    main()
