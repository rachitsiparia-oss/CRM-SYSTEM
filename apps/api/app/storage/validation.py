"""Product image upload validation — SECURITY_PERFORMANCE_AND_QUALITY.md
section 9 ("file extension checks plus MIME checks plus signature checks"),
CORE_CRM_MODULES.md section 7.11 ("validated file type and size").

Deliberately minimal, per this phase's own instruction ("no image AI, no
CDN migration, no optimization pipeline beyond basic validation"): one
clean re-encode to strip metadata (SECURITY_PERFORMANCE_AND_QUALITY.md
section 9.4, "malicious metadata"), no derivative sizes, no quality
tuning, no format conversion beyond what the upload already was.

Malware scanning (section 9.3's quarantine/scan/clean flow) is not
implemented — no scanning provider is configured or approved anywhere in
TOOLS.md, so pretending to scan would be a fake integration
(CLAUDE.md section 16). File-signature verification via Pillow decode
(this module) is real; a separate scanning step remains a documented gap
until a provider is chosen.
"""

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_DIMENSION_PX = 4000

# Extension/declared-MIME/actual-decoded-format must all agree — this is
# what turns "checked the extension" into "checked the file signature."
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class ImageValidationError(ValueError):
    """Raised for any upload that fails validation — the router turns this
    into a 400/422, never a raw 500."""


@dataclass(frozen=True)
class ValidatedImage:
    mime_type: str
    width: int
    height: int
    file_size_bytes: int
    normalized_bytes: bytes


def _extension_of(filename: str) -> str:
    dot_index = filename.rfind(".")
    return filename[dot_index:].lower() if dot_index != -1 else ""


def validate_image_upload(
    *, data: bytes, filename: str, declared_content_type: str
) -> ValidatedImage:
    if len(data) == 0:
        raise ImageValidationError("The uploaded file is empty.")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ImageValidationError(
            f"The file is too large — the limit is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    extension = _extension_of(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            "Unsupported file extension — only .jpg, .jpeg, .png, and .webp are allowed."
        )
    if declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise ImageValidationError(
            "Unsupported content type — only JPEG, PNG, and WEBP images are allowed."
        )
    if ALLOWED_EXTENSIONS[extension] != declared_content_type:
        raise ImageValidationError("The file extension does not match its declared content type.")

    # Decompression-bomb guard (SECURITY_PERFORMANCE_AND_QUALITY.md section
    # 9.4) — Pillow refuses to decode above this pixel count.
    original_max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_DIMENSION_PX * MAX_DIMENSION_PX
    try:
        try:
            with Image.open(io.BytesIO(data)) as probe:
                probe.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageValidationError(
                "The file could not be read as a valid image — it may be corrupted or not a "
                "real image despite its extension."
            ) from exc

        with Image.open(io.BytesIO(data)) as image:
            image.load()
            actual_format = image.format
            expected_format = ALLOWED_CONTENT_TYPES[declared_content_type]
            if actual_format != expected_format:
                raise ImageValidationError(
                    f"The file's actual format ({actual_format}) does not match its declared "
                    f"content type ({declared_content_type})."
                )

            width, height = image.size
            if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
                raise ImageValidationError(
                    f"Image dimensions ({width}x{height}) exceed the "
                    f"{MAX_DIMENSION_PX}x{MAX_DIMENSION_PX} limit."
                )

            # Re-encode from decoded pixel data only — this is what strips
            # EXIF/XMP metadata and any non-pixel payload a crafted file
            # might carry, without resizing or recompressing beyond the
            # format's own defaults.
            normalized = io.BytesIO()
            if expected_format == "JPEG":
                image.convert("RGB").save(normalized, format="JPEG", quality=90)
            else:
                image.save(normalized, format=expected_format)
    finally:
        Image.MAX_IMAGE_PIXELS = original_max_pixels

    normalized_bytes = normalized.getvalue()
    return ValidatedImage(
        mime_type=declared_content_type,
        width=width,
        height=height,
        file_size_bytes=len(normalized_bytes),
        normalized_bytes=normalized_bytes,
    )
