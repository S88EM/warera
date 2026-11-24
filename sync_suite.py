#!/usr/bin/env python3
"""
WarEra Suite Automatic Codebase Synchronizer.
Guarantees that `api/` is the Single Source of Truth (SSOT).
Synchronizes Python modules, HTML templates, and configurations into `warera_suite/api/`.
Cleans up obsolete files and keeps Home Assistant Add-on in 100% sync.
Can be executed manually, in CI/CD, or automatically via git pre-commit hook.
"""

import filecmp
import os
import re
import shutil
import stat
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
API_DIR = BASE_DIR / "api"
SUITE_API_DIR = BASE_DIR / "warera_suite" / "api"

EXCLUDE_NAMES = {
    ".env",
    "API_key.txt",
    "__pycache__",
    "versions",
    "market_history.db",
    "clan_history.db",
    "countries_cache.json",
    "regions_cache.json",
    "bot_subscribers.json",
    ".git",
}

EXCLUDE_EXTENSIONS = {
    ".db",
    ".pyc",
    ".pyo",
    ".log",
    ".token",
    ".key",
}


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_NAMES or part.startswith(".env"):
            return True
    if path.suffix in EXCLUDE_EXTENSIONS:
        return True
    return False


def sync_codebase():
    if not API_DIR.exists():
        print(f"❌ Error: {API_DIR} does not exist!")
        sys.exit(1)

    SUITE_API_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    updated = 0
    deleted = 0

    # 1. Gather all files in api/
    api_files = {}
    for p in API_DIR.rglob("*"):
        if p.is_file() and not should_skip(p.relative_to(API_DIR)):
            api_files[p.relative_to(API_DIR)] = p

    # 2. Gather all files in warera_suite/api/
    suite_files = {}
    for p in SUITE_API_DIR.rglob("*"):
        if p.is_file() and not should_skip(p.relative_to(SUITE_API_DIR)):
            suite_files[p.relative_to(SUITE_API_DIR)] = p

    # 3. Copy / update from api/ -> warera_suite/api/
    for rel_path, src_path in api_files.items():
        dest_path = SUITE_API_DIR / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if not dest_path.exists():
            shutil.copy2(src_path, dest_path)
            copied += 1
        elif not filecmp.cmp(src_path, dest_path, shallow=False):
            shutil.copy2(src_path, dest_path)
            updated += 1

    # 4. Remove obsolete files from warera_suite/api/ that no longer exist in api/
    for rel_path, dest_path in suite_files.items():
        if rel_path not in api_files:
            try:
                dest_path.unlink()
                deleted += 1
            except Exception:
                pass

    # 5. Clean up empty directories in warera_suite/api/
    for d in sorted(SUITE_API_DIR.rglob("*"), reverse=True):
        if d.is_dir() and d.name != "__pycache__":
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass

    # 6. Sync requirements.txt to warera_suite/requirements.txt
    api_req = API_DIR / "requirements.txt"
    suite_req = BASE_DIR / "warera_suite" / "requirements.txt"
    if api_req.exists():
        lines = [line.strip() for line in api_req.read_text(encoding="utf-8").splitlines() if line.strip()]
        # Add anyio if not present
        if not any("anyio" in line for line in lines):
            lines.append("anyio>=4.0.0")
        suite_req.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"✨ [Sync Suite] Готово: скопійовано {copied}, оновлено {updated}, видалено застарілих {deleted}")
    return {"copied": copied, "updated": updated, "deleted": deleted}


def bump_version():
    """Increments patch version in warera_suite/config.yaml and APP_VERSION in api/config.py."""
    suite_cfg = BASE_DIR / "warera_suite" / "config.yaml"
    if suite_cfg.exists():
        text = suite_cfg.read_text(encoding="utf-8")
        m = re.search(r'^(version:\s*["\']?)(\d+)\.(\d+)\.(\d+)(["\']?)', text, re.M)
        if m:
            major, minor, patch = int(m.group(2)), int(m.group(3)), int(m.group(4)) + 1
            new_ver = f"{major}.{minor}.{patch}"
            text = text[:m.start()] + f"{m.group(1)}{new_ver}{m.group(5)}" + text[m.end():]
            suite_cfg.write_text(text, encoding="utf-8")
            print(f"🔖 [Version Bump] warera_suite/config.yaml -> {new_ver}")

    api_cfg = API_DIR / "config.py"
    if api_cfg.exists():
        text = api_cfg.read_text(encoding="utf-8")
        m = re.search(r'^(APP_VERSION\s*=\s*["\']b\.\d+\.)(\d+)(["\'])', text, re.M)
        if m:
            new_build = int(m.group(2)) + 1
            text = text[:m.start()] + f"{m.group(1)}{new_build}{m.group(3)}" + text[m.end():]
            api_cfg.write_text(text, encoding="utf-8")
            print(f"🔖 [Version Bump] api/config.py -> b.0001.{new_build}")


def install_git_hook():
    """Installs or updates .git/hooks/pre-commit to auto-bump version (if not staged) and sync_suite.py."""
    git_dir = BASE_DIR / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        return

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    hook_script = """#!/bin/sh
# Auto-bump HA add-on version if warera_suite/config.yaml was not already bumped, and sync api/ -> warera_suite/api/
BUMP_FLAG=""
if ! git diff --cached --name-only | grep -q "^warera_suite/config.yaml$"; then
    BUMP_FLAG="--bump"
fi
python3 sync_suite.py $BUMP_FLAG 2>/dev/null || python sync_suite.py $BUMP_FLAG 2>/dev/null || py sync_suite.py $BUMP_FLAG 2>/dev/null
git add warera_suite/config.yaml api/config.py warera_suite/api/ warera_suite/requirements.txt 2>/dev/null
exit 0
"""
    try:
        hook_file.write_text(hook_script, encoding="utf-8")
        # Make executable
        st = hook_file.stat()
        hook_file.chmod(st.st_mode | stat.S_IEXEC)
        print("✓ [Git Hook] Встановлено автоматичний pre-commit hook для синхронізації та версіонування")
    except Exception as e:
        print(f"⚠️ Не вдалося записати git hook: {e}")


if __name__ == "__main__":
    if "--bump" in sys.argv:
        bump_version()
    sync_codebase()
    if "--install-hook" in sys.argv or not (BASE_DIR / ".git" / "hooks" / "pre-commit").exists():
        install_git_hook()
