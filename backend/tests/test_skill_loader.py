"""
Tests for skill_loader.py — scanning public and private skill directories.
"""
import os
import pytest

import skill_loader


VALID_FRONTMATTER = """\
---
name: my-skill
category: writing
description: Does something useful.
---
# My Skill
"""

MALFORMED_FRONTMATTER = """\
---
name: [unclosed bracket
: bad: yaml:
---
# Body
"""

NO_FRONTMATTER = """\
# Just a heading
No frontmatter here.
"""


class TestScan:
    def test_public_skill_returned_with_public_visibility(self, tmp_backend):
        """Skills in skills/public/ have visibility='public'."""
        skills = skill_loader.scan()
        public = [s for s in skills if s["visibility"] == "public"]
        assert len(public) >= 1

    def test_private_skill_returned_with_private_visibility(self, tmp_backend):
        """Skills in skills/private/ have visibility='private'."""
        priv_dir = tmp_backend / "skills" / "private" / "priv-skill"
        priv_dir.mkdir(parents=True, exist_ok=True)
        (priv_dir / "SKILL.md").write_text("""\
---
name: priv-skill
category: private-cat
description: A private skill.
---
# Private
""")
        skills = skill_loader.scan()
        private = [s for s in skills if s["visibility"] == "private"]
        assert any(s["name"] == "priv-skill" for s in private)

    def test_both_public_and_private_returned(self, tmp_backend):
        """scan() returns skills from both directories."""
        priv_dir = tmp_backend / "skills" / "private" / "priv2"
        priv_dir.mkdir(parents=True, exist_ok=True)
        (priv_dir / "SKILL.md").write_text("---\nname: priv2\ndescription: x.\ncategory: util\n---\n# x")
        skills = skill_loader.scan()
        visibilities = {s["visibility"] for s in skills}
        assert "public" in visibilities
        assert "private" in visibilities

    def test_skill_metadata_from_frontmatter(self, tmp_backend):
        """name, description, category are read from YAML frontmatter."""
        skill_dir = tmp_backend / "skills" / "public" / "meta-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(VALID_FRONTMATTER)
        skills = skill_loader.scan()
        skill = next((s for s in skills if s["name"] == "my-skill"), None)
        assert skill is not None
        assert skill["description"] == "Does something useful."
        assert skill["category"] == "writing"

    def test_skill_md_path_uses_forward_slashes(self, tmp_backend):
        """skill_md_path uses forward slashes regardless of OS."""
        skills = skill_loader.scan()
        for s in skills:
            assert "\\" not in s["skill_md_path"]

    def test_skill_md_path_is_relative_to_backend(self, tmp_backend):
        """skill_md_path starts with 'skills/' (relative path, not absolute)."""
        skills = skill_loader.scan()
        for s in skills:
            # The path should not be an absolute path starting with /
            assert not s["skill_md_path"].startswith("/")

    def test_skill_without_frontmatter_falls_back_to_folder_name(self, tmp_backend):
        """A SKILL.md without frontmatter uses the directory name and 'utility' category."""
        skill_dir = tmp_backend / "skills" / "public" / "no-front"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(NO_FRONTMATTER)
        skills = skill_loader.scan()
        skill = next((s for s in skills if "no-front" in s["name"]), None)
        assert skill is not None
        assert skill["category"] == "utility"

    def test_malformed_yaml_frontmatter_skipped_gracefully(self, tmp_backend):
        """A skill with malformed YAML frontmatter does not crash scan()."""
        skill_dir = tmp_backend / "skills" / "public" / "bad-yaml"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(MALFORMED_FRONTMATTER)
        # Must not raise
        skills = skill_loader.scan()
        # bad-yaml skill might or might not be included — the point is no crash
        assert isinstance(skills, list)

    def test_empty_skills_directory_returns_empty_list(self, tmp_backend):
        """When no SKILL.md files exist, scan() returns an empty list."""
        # Remove the sample skill
        sample = tmp_backend / "skills" / "public" / "test-skill" / "SKILL.md"
        sample.unlink()
        skills = skill_loader.scan()
        assert skills == []

    def test_missing_public_dir_returns_private_skills(self, tmp_backend):
        """If public/ dir doesn't exist, skills from private/ are still returned."""
        import shutil
        shutil.rmtree(str(tmp_backend / "skills" / "public"))
        priv_dir = tmp_backend / "skills" / "private" / "only-priv"
        priv_dir.mkdir(parents=True, exist_ok=True)
        (priv_dir / "SKILL.md").write_text("---\nname: only-priv\ndescription: x.\ncategory: x\n---\n# x")
        skills = skill_loader.scan()
        assert any(s["name"] == "only-priv" for s in skills)

    def test_missing_private_dir_returns_public_skills(self, tmp_backend):
        """If private/ dir doesn't exist, skills from public/ are still returned."""
        import shutil
        shutil.rmtree(str(tmp_backend / "skills" / "private"))
        skills = skill_loader.scan()
        assert any(s["visibility"] == "public" for s in skills)
