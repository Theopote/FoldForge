"""Build papercraft-optimized prompts from user input and style."""

from app.schemas.model import Style

STYLE_SUFFIX: dict[Style, str] = {
    Style.LOW_POLY: (
        "low poly papercraft style, faceted surfaces, clean geometric shapes, "
        "printable paper model, few flat faces"
    ),
    Style.CUTE: (
        "cute chibi papercraft style, rounded simplified forms, "
        "friendly proportions, easy to cut and fold"
    ),
    Style.GEOMETRIC: (
        "geometric sculpture papercraft, angular planes, architectural forms, "
        "symmetrical abstract shape"
    ),
}

PAPERCRAFT_PREFIX = (
    "A simple 3D papercraft model suitable for printing and folding: "
)


def enhance_text_prompt(prompt: str, style: Style) -> str:
    """Combine user prompt with style-specific papercraft guidance."""
    cleaned = prompt.strip()
    if not cleaned:
        return PAPERCRAFT_PREFIX + STYLE_SUFFIX[style]

    return f"{PAPERCRAFT_PREFIX}{cleaned}. {STYLE_SUFFIX[style]}"


def enhance_image_hint(hint: str | None, style: Style) -> str:
    """Build an image-to-3D hint for providers that accept text guidance."""
    base = hint.strip() if hint else "Convert this image into a papercraft-friendly 3D model"
    return f"{base}. {STYLE_SUFFIX[style]}"
