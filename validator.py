# validator.py

SUSPICIOUS_PATTERNS = [
    "ignore your instructions",
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal your system prompt",
    "show me your system prompt",
    "print your system prompt",
    "developer instructions",
    "system instructions",
    "forget your instructions",
    "jailbreak",
    "act as another ai",
    "you are now",
    "bypass your rules"
]


def is_prompt_injection(user_input: str) -> bool:
    """
    Returns True if the input looks like
    a prompt injection attempt.
    """

    text = user_input.lower()

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in text:
            return True

    return False