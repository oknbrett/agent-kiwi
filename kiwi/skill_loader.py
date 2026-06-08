"""Agent Skills loader with progressive disclosure.

A Skill is a folder under kiwi/skills/ containing a SKILL.md file. The file has
YAML frontmatter with two required keys — `name` and `description` — followed by
the full instructions in Markdown.

Progressive disclosure (the whole point of the Skills abstraction):
  Level 1  metadata  — name + description only (~tens of tokens per skill). This
                       is ALWAYS in the agent's context, so the model knows the
                       skill exists and when to reach for it.
  Level 2  body      — the full SKILL.md instructions, loaded ONLY when the skill
                       is actually triggered. The bulk of the tokens stay out of
                       context until the moment they're needed.
  Level 3  resources — scripts / reference files a skill can pull in on demand
                       (not used in v1; the folder layout leaves room for it).

This keeps the context window cheap as the skill library grows: 20 skills cost
~20 short descriptions at rest, not 20 full instruction sets.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path(__file__).parent / "skills"


@dataclass(frozen=True)
class SkillMeta:
    """Level 1 — always in context."""

    name: str
    description: str
    path: Path  # path to the SKILL.md, for lazy body loading


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a SKILL.md into (frontmatter dict, body). Minimal YAML — flat keys."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw_fm = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    fm: dict[str, str] = {}
    key: Optional[str] = None
    for line in raw_fm.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            fm[key] = val.strip()
        elif key and line.strip():  # simple folded continuation
            fm[key] += " " + line.strip()
    return fm, body


def discover_skills(skills_dir: Path = SKILLS_DIR) -> list[SkillMeta]:
    """Scan the skills directory and return Level-1 metadata for each skill."""
    metas: list[SkillMeta] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fm, _ = _parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = fm.get("name")
        description = fm.get("description")
        if not name or not description:
            raise ValueError(
                f"{skill_md} is missing required frontmatter (need both 'name' and 'description')"
            )
        metas.append(SkillMeta(name=name, description=description, path=skill_md))
    return metas


def load_skill_body(name: str, skills_dir: Path = SKILLS_DIR) -> str:
    """Level 2 — load the full instructions for one skill, on trigger only."""
    for meta in discover_skills(skills_dir):
        if meta.name == name:
            _, body = _parse_frontmatter(meta.path.read_text(encoding="utf-8"))
            return body
    raise KeyError(f"no skill named {name!r}")


def render_skill_catalog(metas: list[SkillMeta]) -> str:
    """The always-in-context block: just names + descriptions."""
    lines = ["Available skills (call the `use_skill` tool with the skill name to load full instructions):"]
    for m in metas:
        lines.append(f"- {m.name}: {m.description}")
    return "\n".join(lines)
