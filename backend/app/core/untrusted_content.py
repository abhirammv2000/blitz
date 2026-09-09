"""Marks externally-sourced text so prompts can tell it apart from instructions.

Every scraped page and search result that reaches a prompt in this pipeline
came from a website we don't control. Wrapping it here is a mitigation, not a
guarantee - nothing on the prompt side can make it impossible for adversarial
text to influence a model. The schema validation each agent already does is
the real backstop: if a model does get steered off its output format, that
raises instead of quietly passing attacker-controlled text downstream.
"""

from __future__ import annotations

_OPEN = '<untrusted_web_content source="{source}">'
_CLOSE = "</untrusted_web_content>"


def wrap_untrusted(text: str, source: str) -> str:
    """Delimit text pulled from a third-party page or search result.

    `source` is a short label (e.g. "scraped_website", "search_results") so
    the tag itself says where the content came from.
    """
    return f"{_OPEN.format(source=source)}\n{text}\n{_CLOSE}"
