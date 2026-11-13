# backend/agent/agent_i18n.py — tiny reply-language helper for agent messages.
#
# Voice replies are synthesized in the language of the user's command. Keeping
# agent confirmation text in the same language avoids an English sentence being
# read by a Bengali voice (or the other way around).

from __future__ import annotations

import re

_BN_SCRIPT = re.compile(r"[\u0980-\u09FF]")
_BANGLISH = re.compile(
    r"\b(?:koro|korbo|kore|koren|kholo|khol|chalu|bondho|bondh|khojo|khujo|"
    r"khoroch|taka|gan|chobi|banao|banai|lagbe|dao|den|amar|ami|ekta|notun|"
    r"kaj|kal|aj|sokal|bikal|rat|bhai|plz|pls)\b",
    re.IGNORECASE,
)


def is_bengali(command: str) -> bool:
    text = str(command or "")
    return bool(_BN_SCRIPT.search(text) or _BANGLISH.search(text))


def tr(command: str, english: str, bengali: str) -> str:
    """Return the Bengali string for Bengali/Banglish input, English otherwise."""
    return bengali if is_bengali(command) else english
