import hashlib
import re


def digest(text: str | bytes) -> str:
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def tokenize(text: str) -> list[str]:
    """English words and Chinese single characters/bigrams; no model download."""
    tokens: list[str] = []
    for part in re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", text.lower()):
        if re.fullmatch(r"[a-z0-9_]+", part):
            tokens.append(part)
        else:
            tokens.extend(part)
            tokens.extend(part[i : i + 2] for i in range(len(part) - 1))
    return tokens
