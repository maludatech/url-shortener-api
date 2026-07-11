import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
_DEFAULT_LENGTH = 7


def generate_short_code(length: int = _DEFAULT_LENGTH) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
