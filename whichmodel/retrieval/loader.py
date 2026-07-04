"""Load the markdown knowledge base from disk."""

import logging
from pathlib import Path

import frontmatter

from whichmodel.retrieval.base import KBDoc

log = logging.getLogger(__name__)


def load_kb(kb_dir: Path) -> list[KBDoc]:
    """Parse every .md file under kb_dir into a KBDoc, skipping malformed files."""
    docs: list[KBDoc] = []
    for path in sorted(kb_dir.rglob("*.md")):
        try:
            post = frontmatter.load(path)
            name = str(path.relative_to(kb_dir).with_suffix(""))
            tags = post.get("tags") or []
            docs.append(
                KBDoc(
                    name=name,
                    category=str(post.get("category", "")),
                    tags=tuple(str(t) for t in tags),
                    updated=str(post.get("updated", "")),
                    text=post.content.strip(),
                )
            )
        except Exception as err:
            log.warning("skipping malformed KB doc %s: %s", path, err)
    if not docs:
        log.warning("no KB docs loaded from %s", kb_dir)
    return docs
