#!/usr/bin/env python3
"""Apply platform-specific overlay to sage-loop skills.

Usage:
    python3 scripts/apply_overlay.py claude    # Apply Claude overlay
    python3 scripts/apply_overlay.py codex     # Apply Codex overlay
    python3 scripts/apply_overlay.py --list    # List available overlays
"""

import argparse
import re
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"
OVERLAYS_DIR = ROOT / "overlays"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            fm[key.strip()] = value.strip().strip('"').strip("'")

    return fm, "---" + parts[2]


def write_frontmatter(fm: dict, body: str) -> str:
    """Write YAML frontmatter."""
    lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, str) and (len(value) > 60 or "\n" in value):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + body


def load_overlay(platform: str) -> dict:
    """Load overlay configuration."""
    overlay_file = OVERLAYS_DIR / platform / "model_map.yaml"
    if not overlay_file.exists():
        raise FileNotFoundError(f"Overlay not found: {overlay_file}")

    if HAS_YAML:
        with open(overlay_file) as f:
            return yaml.safe_load(f)
    else:
        # Simple YAML parser fallback
        config = {"models": {}}
        content = overlay_file.read_text()
        current_skill = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if line.endswith(":") and not line.startswith(" "):
                continue
            # Parse skill: { model: X, ... }
            match = re.match(r'(\w[\w-]*): \{(.+)\}', line)
            if match:
                skill = match.group(1)
                props = {}
                for prop in match.group(2).split(","):
                    if ":" in prop:
                        k, v = prop.split(":", 1)
                        props[k.strip()] = v.strip()
                config["models"][skill] = props
        return config


def find_skill_source(skill_name: str) -> Path | None:
    """Find skill source file, preferring directory version.

    Priority:
    1. skills/{name}/SKILL.md (detailed version)
    2. skills/{name}.md (simple version)
    """
    # Prefer directory version (has more content like guides, scripts)
    dir_skill = SKILLS_DIR / skill_name / "SKILL.md"
    if dir_skill.exists():
        return dir_skill

    # Fall back to simple .md file
    file_skill = SKILLS_DIR / f"{skill_name}.md"
    if file_skill.exists():
        return file_skill

    return None


def apply_claude_overlay(config: dict, verbose: bool = True):
    """Apply Claude overlay to skills."""
    skills_path = Path(config.get("skills_path", "~/.claude/skills/")).expanduser()
    skills_path.mkdir(parents=True, exist_ok=True)

    for skill_name, settings in config.get("models", {}).items():
        # Find source skill (directory version preferred)
        src_file = find_skill_source(skill_name)
        if not src_file:
            if verbose:
                print(f"  [SKIP] {skill_name}: source not found")
            continue

        content = src_file.read_text()
        fm, body = parse_frontmatter(content)

        # Apply model
        if "model" in settings:
            fm["model"] = settings["model"]

        # Apply ultrathink
        if settings.get("thinking") == "ultrathink":
            if "ultrathink" not in body.lower():
                body = body.lstrip("-").lstrip("\n")
                body = "\n\n# ultrathink\n" + body

        # Write to Claude skills directory
        dst_dir = skills_path / skill_name
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "SKILL.md").write_text(write_frontmatter(fm, body))

        # Copy additional files
        src_dir = src_file.parent
        for item in src_dir.iterdir():
            if item.name in ("SKILL.md", "__pycache__") or item.name.endswith(".md"):
                continue
            if item.is_dir():
                import shutil
                dst = dst_dir / item.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst, ignore=shutil.ignore_patterns("__pycache__"))

        if verbose:
            thinking = " + ultrathink" if settings.get("thinking") else ""
            print(f"  [OK] {skill_name} → {settings.get('model', '?')}{thinking}")

    if verbose:
        print(f"\nSkills installed to: {skills_path}")


def apply_codex_overlay(config: dict, verbose: bool = True):
    """Apply Codex overlay to skills."""
    skills_path = Path(config.get("skills_path", "~/.codex/skills/")).expanduser()
    skills_path.mkdir(parents=True, exist_ok=True)

    profiles = []

    for skill_name, settings in config.get("models", {}).items():
        # Find source skill (directory version preferred)
        src_file = find_skill_source(skill_name)
        if not src_file:
            if verbose:
                print(f"  [SKIP] {skill_name}: source not found")
            continue

        content = src_file.read_text()
        fm, body = parse_frontmatter(content)

        # Remove Claude-specific fields
        fm.pop("model", None)
        fm.pop("alias", None)

        # Add metadata for cross-platform
        fm["metadata"] = {"sage-loop-skill": skill_name}

        # Write to Codex skills directory
        dst_dir = skills_path / skill_name
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "SKILL.md").write_text(write_frontmatter(fm, body))

        # Build profile entry
        profile = f'[profiles.{skill_name}]\nmodel = "{settings.get("model", "gpt-5.2-codex")}"'
        if "reasoning_effort" in settings:
            profile += f'\nmodel_reasoning_effort = "{settings["reasoning_effort"]}"'
        profiles.append(profile)

        if verbose:
            reasoning = f" + reasoning:{settings['reasoning_effort']}" if settings.get("reasoning_effort") else ""
            print(f"  [OK] {skill_name} → {settings.get('model', '?')}{reasoning}")

    # Write profiles.toml
    profiles_content = "# sage-loop Codex profiles\n# Add to ~/.codex/config.toml\n\n" + "\n\n".join(profiles)
    (skills_path / "profiles.toml").write_text(profiles_content)

    if verbose:
        print(f"\nSkills installed to: {skills_path}")
        print(f"Profiles saved to: {skills_path / 'profiles.toml'}")


def list_overlays():
    """List available overlays."""
    print("Available overlays:")
    for overlay_dir in OVERLAYS_DIR.iterdir():
        if overlay_dir.is_dir() and (overlay_dir / "model_map.yaml").exists():
            print(f"  - {overlay_dir.name}")


def main():
    parser = argparse.ArgumentParser(description="Apply platform overlay to sage-loop skills")
    parser.add_argument("platform", nargs="?", help="Platform: claude, codex")
    parser.add_argument("--list", action="store_true", help="List available overlays")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    if args.list:
        list_overlays()
        return

    if not args.platform:
        parser.print_help()
        return

    config = load_overlay(args.platform)
    verbose = not args.quiet

    if verbose:
        print(f"Applying {args.platform} overlay...")

    if args.platform == "claude":
        apply_claude_overlay(config, verbose)
    elif args.platform == "codex":
        apply_codex_overlay(config, verbose)
    else:
        print(f"Unknown platform: {args.platform}")
        print("Use --list to see available overlays")


if __name__ == "__main__":
    main()
