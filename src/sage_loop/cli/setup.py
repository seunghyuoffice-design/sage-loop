#!/usr/bin/env python3
"""
Sage Loop Setup - Install skills and hooks for ONE platform

Usage:
    sage-loop-setup --platform claude        # Install for Claude Code
    sage-loop-setup --platform codex         # Install for Codex
    sage-loop-setup --platform antigravity   # Install for Antigravity
    sage-loop-setup --check                  # Check installation status
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def get_package_root() -> Path:
    """Get sage-loop package root directory."""
    return Path(__file__).resolve().parent.parent.parent.parent


def check_installation(platform: str) -> dict[str, bool]:
    """Check if skills and hooks are installed for given platform."""
    if platform == "claude":
        claude_home = Path.home() / ".claude"
        return {
            "skills": (claude_home / "skills").exists() and len(list((claude_home / "skills").glob("*"))) > 0,
            "hooks": (claude_home / "hooks").exists() and len(list((claude_home / "hooks").glob("*.py"))) > 0,
        }
    elif platform == "codex":
        codex_home = Path.home() / ".codex"
        return {
            "skills": (codex_home / "skills").exists() and len(list((codex_home / "skills").glob("*"))) > 0,
            "config": (codex_home / "config.toml").exists(),
        }
    elif platform == "antigravity":
        antigravity_home = Path.home() / ".gemini" / "antigravity" / "global_skills"
        return {
            "skills": antigravity_home.exists() and len(list(antigravity_home.glob("*"))) > 0,
        }
    else:
        return {}


def install_git_hooks(package_root: Path, quiet: bool = False) -> bool:
    """Install Git hooks to .git/hooks/"""
    git_hooks_dir = package_root / ".git" / "hooks"
    if not git_hooks_dir.exists():
        if not quiet:
            print("⚠ Not a git repository - skipping git hooks")
        return True  # Not an error

    source_hooks = package_root / "git-hooks"
    if not source_hooks.exists():
        if not quiet:
            print("⚠ git-hooks directory not found - skipping")
        return True

    copied = 0
    for hook_file in source_hooks.iterdir():
        if hook_file.is_file():
            dest = git_hooks_dir / hook_file.name
            shutil.copy2(hook_file, dest)
            dest.chmod(0o755)
            copied += 1

    if not quiet and copied > 0:
        print(f"✓ Installed {copied} git hooks")

    return True


def install_claude(package_root: Path, quiet: bool = False, with_dokseol: bool = False) -> bool:
    """Install for Claude Code: skills and hooks to ~/.claude/"""
    claude_home = Path.home() / ".claude"

    # 0. Git hooks (공통)
    install_git_hooks(package_root, quiet)

    # 1. Skills
    source_skills = package_root / "skills"
    target_skills = claude_home / "skills"

    if not source_skills.exists():
        if not quiet:
            print(f"✗ Skills directory not found: {source_skills}")
        return False

    target_skills.mkdir(parents=True, exist_ok=True)

    copied = 0
    for item in source_skills.iterdir():
        if item.name.startswith("."):
            continue

        dest = target_skills / item.name

        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
            copied += 1
        elif item.suffix == ".md":
            shutil.copy2(item, dest)
            copied += 1

    if not quiet:
        print(f"✓ Installed {copied} skills to {target_skills}")

    # 2. Hooks from overlays/claude/hooks/
    source_hooks = package_root / "overlays" / "claude" / "hooks"
    target_hooks = claude_home / "hooks"

    if not source_hooks.exists():
        if not quiet:
            print(f"⚠ Hooks directory not found: {source_hooks}")
        return True  # Skills만 설치해도 성공으로 간주

    target_hooks.mkdir(parents=True, exist_ok=True)

    hook_copied = 0
    for item in source_hooks.iterdir():
        if item.is_dir():
            continue  # Skip subdirectories (e.g., optional/)
        if item.suffix in [".py", ".sh"]:
            shutil.copy2(item, target_hooks / item.name)
            if item.suffix == ".sh":
                (target_hooks / item.name).chmod(0o755)
            hook_copied += 1

    if not quiet:
        print(f"✓ Installed {hook_copied} hooks to {target_hooks}")

    # 3. Optional: Dokseol hooks
    if with_dokseol:
        source_dokseol = source_hooks / "optional"
        if source_dokseol.exists():
            dokseol_copied = 0
            for item in source_dokseol.iterdir():
                if item.suffix in [".py", ".yaml"]:
                    shutil.copy2(item, target_hooks / item.name)
                    if item.suffix == ".py":
                        (target_hooks / item.name).chmod(0o755)
                    dokseol_copied += 1
            if not quiet:
                print(f"✓ Installed {dokseol_copied} dokseol hooks to {target_hooks}")

    return True


def install_codex(package_root: Path, quiet: bool = False, with_dokseol: bool = False) -> bool:
    """Install for Codex: apply overlay and merge config"""
    # 1. Apply overlay (with dokseol option)
    result = apply_overlay("codex", package_root, quiet, with_dokseol)
    if not result:
        return False

    # 2. Merge config.toml from overlays/codex/
    codex_home = Path.home() / ".codex"
    codex_home.mkdir(parents=True, exist_ok=True)

    config_source = package_root / "overlays" / "codex" / "config.toml"
    config_target = codex_home / "config.toml"

    if config_source.exists():
        if config_target.exists():
            # Merge: append if not exists
            existing = config_target.read_text()
            new_content = config_source.read_text()

            if "agents.sage-loop" not in existing:
                with config_target.open("a") as f:
                    f.write("\n")
                    f.write(new_content)
                if not quiet:
                    print(f"✓ Merged config to {config_target}")
        else:
            shutil.copy2(config_source, config_target)
            if not quiet:
                print(f"✓ Copied config to {config_target}")

    # 3. Merge instructions.md from overlays/codex/
    instructions_source = package_root / "overlays" / "codex" / "instructions.md"
    instructions_target = codex_home / "instructions.md"

    if instructions_source.exists():
        if instructions_target.exists():
            existing = instructions_target.read_text()
            new_content = instructions_source.read_text()

            if "Sage Loop" not in existing:
                with instructions_target.open("a") as f:
                    f.write("\n")
                    f.write(new_content)
                if not quiet:
                    print(f"✓ Merged instructions to {instructions_target}")
        else:
            shutil.copy2(instructions_source, instructions_target)
            if not quiet:
                print(f"✓ Copied instructions to {instructions_target}")

    return True


def install_antigravity(package_root: Path, quiet: bool = False, with_dokseol: bool = False) -> bool:
    """Install for Antigravity: apply overlay"""
    return apply_overlay("antigravity", package_root, quiet, with_dokseol)


def apply_overlay(platform: str, package_root: Path, quiet: bool = False, with_dokseol: bool = False) -> bool:
    """Apply platform-specific overlay."""
    overlay_script = package_root / "scripts" / "apply_overlay.py"

    if not overlay_script.exists():
        if not quiet:
            print(f"⚠ Overlay script not found: {overlay_script}")
        return False

    try:
        args = [sys.executable, str(overlay_script), platform]
        if quiet:
            args.append("-q")
        if with_dokseol:
            args.append("--with-dokseol")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )
        if not quiet:
            print(f"✓ Applied {platform} overlay")
        return True
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(f"✗ Failed to apply overlay: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sage Loop setup utility")
    parser.add_argument("--platform", choices=["claude", "codex", "antigravity"], required=False, help="Platform to install for")
    parser.add_argument("--check", action="store_true", help="Check installation status")
    parser.add_argument("--with-dokseol", action="store_true", help="Install with dokseol (독설) messages")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    package_root = get_package_root()

    # Check mode
    if args.check:
        if not args.platform:
            print("Error: --check requires --platform")
            sys.exit(1)

        status = check_installation(args.platform)
        for key, value in status.items():
            print(f"{key}: {'✓' if value else '✗'}")
        sys.exit(0 if all(status.values()) else 1)

    # Install mode
    if not args.platform:
        print("Error: --platform required (claude, codex, or antigravity)")
        sys.exit(1)

    if not args.quiet:
        print(f"Sage Loop Setup - {args.platform}")
        if args.with_dokseol:
            print("(with dokseol)")
        print("=" * 50)

    # Install based on platform
    success = False
    if args.platform == "claude":
        success = install_claude(package_root, args.quiet, args.with_dokseol)
    elif args.platform == "codex":
        success = install_codex(package_root, args.quiet, args.with_dokseol)
    elif args.platform == "antigravity":
        success = install_antigravity(package_root, args.quiet, args.with_dokseol)

    if success:
        if not args.quiet:
            print(f"\n✓ Sage Loop setup complete for {args.platform}!")
    else:
        print(f"\n✗ Setup failed for {args.platform}")
        sys.exit(1)


if __name__ == "__main__":
    main()
