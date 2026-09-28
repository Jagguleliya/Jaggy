"""
JAGY Built-in API Keys & Defaults.
These keys are bundled with the app so users never need to provide their own.
The Gemini API key is on the free tier — if users want higher limits, they can
supply their own key in config/config.yaml and it will override this default.
"""
import base64

_B1 = "QVEuQWI4Uk42TFFYNGJxbjA4T0RvckZ1YWR6ZVVpS0Q0RjFQWW42TkRIZ3JhSm10UzFYQ1E="
_B2 = "TUY3dWliVmFQN3haQzVMVWE1ZGR5N1RIWklVZHYyMW91dm9kQUVWT1owanJBb3BnbldSVkZBQ3Y="

def _decode(b: str) -> str:
    try:
        return base64.b64decode(b).decode("utf-8")
    except Exception:
        return ""

BUILTIN_GEMINI_KEY = _decode(_B1)
BUILTIN_PEXELS_KEY = _decode(_B2)


def get_gemini_key(config: dict = None) -> str:
    """
    Returns the best available Gemini API key.
    Priority: user's config.yaml key > built-in default key.
    """
    if config:
        user_key = config.get("api_keys", {}).get("gemini", "")
        if user_key and user_key != "YOUR_GEMINI_API_KEY" and len(user_key) > 10:
            return user_key
    return BUILTIN_GEMINI_KEY


def get_pexels_key(config: dict = None) -> str:
    """
    Returns the best available Pexels API key.
    Priority: user's config.yaml key > built-in default key.
    """
    if config:
        user_key = config.get("api_keys", {}).get("pexels", "")
        if user_key and user_key != "YOUR_PEXELS_API_KEY" and len(user_key) > 10:
            return user_key
    return BUILTIN_PEXELS_KEY
