"""
Input guardrails — validation, prompt injection detection, topic scoping.
"""

import re

MAX_MESSAGE_LENGTH = 2000

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+above",
    r"system\s*prompt\s*:",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new)\s+(?:ai|assistant|bot)",
    r"forget\s+(all\s+)?(your|previous)\s+(instructions|rules)",
    r"disregard\s+(all\s+)?previous",
    r"(?:act|behave)\s+as\s+(?:if\s+)?(?:you\s+(?:are|were))",
    r"override\s+(?:your\s+)?(?:instructions|rules|guidelines)",
    r"\[system\]",
    r"<\|(?:im_start|system)\|>",
]

OFF_TOPIC_KEYWORDS = [
    "write me a poem", "tell me a joke", "recipe for",
    "what is the meaning of life", "play a game",
    "write a story", "sing a song",
]


class InputGuard:
    def __init__(self):
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def check(self, message: str) -> tuple[bool, str]:
        if not message or not message.strip():
            return False, "Empty message."

        if len(message) > MAX_MESSAGE_LENGTH:
            return False, f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters."

        for pattern in self._injection_re:
            if pattern.search(message):
                return False, "Message flagged for potential prompt injection."

        msg_lower = message.lower()
        for keyword in OFF_TOPIC_KEYWORDS:
            if keyword in msg_lower:
                return False, "This query appears to be outside the automotive software integration domain."

        return True, ""
