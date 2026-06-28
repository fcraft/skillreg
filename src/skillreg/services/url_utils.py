"""URL normalization utilities.

Merges ``sshToHttps`` (skill-registry.js:26) and ``resolveRepoUrl``
(remote-syncer.js:187) into a single module.
"""

from __future__ import annotations

import re

_SSH_PATTERN = re.compile(r"git@([^:]+):(.+?)(?:\.git)?$")


def normalize_git_url(url: str | None) -> str | None:
    """Normalize a git remote URL to HTTPS form.

    - ``git@github.com:fcraft/skillreg.git`` → ``https://github.com/fcraft/skillreg``
    - ``https://github.com/fcraft/skillreg.git`` → ``https://github.com/fcraft/skillreg``
    - ``None`` / unrecognized → ``None``
    """
    if not url:
        return None
    m = _SSH_PATTERN.match(url)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    if url.startswith("http"):
        return url.removesuffix(".git")
    return None
