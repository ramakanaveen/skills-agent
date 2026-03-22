import os
import yaml
from typing import List, Dict

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")
PUBLIC_DIR = os.path.join(SKILLS_DIR, "public")
PRIVATE_DIR = os.path.join(SKILLS_DIR, "private")


def _scan_dir(root_dir: str, visibility: str) -> List[Dict]:
    """Scan one skills directory (public or private) and return metadata list."""
    skills = []
    if not os.path.isdir(root_dir):
        return skills

    backend_dir = os.path.dirname(__file__)

    for dirpath, _, files in os.walk(root_dir):
        if "SKILL.md" not in files:
            continue

        skill_md_abs = os.path.join(dirpath, "SKILL.md")
        rel_path = os.path.relpath(skill_md_abs, backend_dir).replace(os.sep, "/")

        try:
            with open(skill_md_abs, encoding="utf-8") as f:
                content = f.read()

            name = os.path.basename(dirpath)
            description = f"Skill: {name}"
            category = "utility"

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        name = frontmatter.get("name", name)
                        desc = frontmatter.get("description", description)
                        description = desc.strip() if isinstance(desc, str) else description
                        category = frontmatter.get("category", "utility")

            skills.append({
                "name": name,
                "description": description,
                "skill_md_path": rel_path,
                "visibility": visibility,
                "category": category,
            })

        except Exception as e:
            print(f"Error loading skill {skill_md_abs}: {e}")

    return skills


def scan() -> List[Dict]:
    """
    Scan skills/public/ and skills/private/.
    Both dirs are visible to the agent; only public/ is committed to git.
    Returns list of { name, description, skill_md_path, visibility }
    Re-scanned on every /api/run call so new skills are immediately available.
    """
    return _scan_dir(PUBLIC_DIR, "public") + _scan_dir(PRIVATE_DIR, "private")
