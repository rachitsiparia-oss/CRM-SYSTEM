"""Security tests for the file-upload validation functions themselves —
`app.storage.validation.validate_image_upload` (product images) and
`app.knowledge.attachments.validate_attachment_upload` (PDF/DOCX/CSV/image
knowledge & staff-document attachments). TOOLS.md section 12.6 ("file-upload
abuse tests" as an approved security-testing category).

These were reviewed for correctness in Phase 16 (docs/phase-16/
SECURITY_AUDIT_REPORT.md finding 6) but never had direct unit tests before
this file — the scan-hook wiring was tested (test_attachment_scanning.py),
the underlying extension/MIME/signature checks were not.
"""

import io

import pytest
from app.knowledge.attachments import AttachmentValidationError, validate_attachment_upload
from app.storage.validation import ImageValidationError, validate_image_upload
from PIL import Image


def _real_png_bytes(size: tuple[int, int] = (4, 4)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


# --- app.storage.validation.validate_image_upload ---------------------------


def test_validate_image_upload_accepts_a_real_png() -> None:
    data = _real_png_bytes()
    result = validate_image_upload(
        data=data, filename="photo.png", declared_content_type="image/png"
    )
    assert result.mime_type == "image/png"
    assert result.width == 4
    assert result.height == 4
    assert len(result.normalized_bytes) > 0


def test_validate_image_upload_strips_exif_metadata() -> None:
    # A JPEG carrying real EXIF metadata — the re-encode (decode pixels,
    # save fresh) must not carry it through, since arbitrary EXIF/XMP is
    # exactly the "malicious metadata" payload vector this step guards
    # against (SECURITY_PERFORMANCE_AND_QUALITY.md section 9.4).
    buf = io.BytesIO()
    image = Image.new("RGB", (4, 4), color=(0, 255, 0))
    exif = image.getexif()
    exif[0x9286] = "arbitrary user comment payload"  # UserComment tag
    image.save(buf, format="JPEG", exif=exif)
    data = buf.getvalue()

    with_exif = Image.open(io.BytesIO(data))
    assert len(with_exif.getexif()) > 0  # sanity: the input really carries EXIF

    result = validate_image_upload(
        data=data, filename="photo.jpg", declared_content_type="image/jpeg"
    )
    stripped = Image.open(io.BytesIO(result.normalized_bytes))
    assert len(stripped.getexif()) == 0


def test_validate_image_upload_rejects_empty_file() -> None:
    with pytest.raises(ImageValidationError):
        validate_image_upload(data=b"", filename="photo.png", declared_content_type="image/png")


def test_validate_image_upload_rejects_oversized_file() -> None:
    oversized = _real_png_bytes() + b"\x00" * (6 * 1024 * 1024)
    with pytest.raises(ImageValidationError):
        validate_image_upload(
            data=oversized, filename="photo.png", declared_content_type="image/png"
        )


def test_validate_image_upload_rejects_unsupported_extension() -> None:
    with pytest.raises(ImageValidationError):
        validate_image_upload(
            data=_real_png_bytes(), filename="photo.gif", declared_content_type="image/gif"
        )


def test_validate_image_upload_rejects_extension_content_type_mismatch() -> None:
    with pytest.raises(ImageValidationError):
        validate_image_upload(
            data=_real_png_bytes(), filename="photo.png", declared_content_type="image/jpeg"
        )


def test_validate_image_upload_rejects_signature_mismatch() -> None:
    # A plain text payload disguised with a .png extension and an
    # image/png declared content type — the extension/MIME pair matches,
    # but Pillow cannot decode it as a real image. This is exactly the
    # attack the file-signature check exists to catch.
    fake = b"not actually a png file, just text pretending to be one"
    with pytest.raises(ImageValidationError):
        validate_image_upload(data=fake, filename="photo.png", declared_content_type="image/png")


def test_validate_image_upload_rejects_declared_format_not_matching_actual() -> None:
    # A real PNG, declared and extensioned as a JPEG — extension/MIME agree
    # with each other but not with the file's actual decoded format.
    png_bytes = _real_png_bytes()
    with pytest.raises(ImageValidationError):
        validate_image_upload(
            data=png_bytes, filename="photo.jpg", declared_content_type="image/jpeg"
        )


# --- app.knowledge.attachments.validate_attachment_upload -------------------


def test_validate_attachment_upload_accepts_a_real_pdf_signature() -> None:
    data = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< >>\nendobj\n"
    result = validate_attachment_upload(
        data=data, filename="doc.pdf", declared_content_type="application/pdf"
    )
    assert result.mime_type == "application/pdf"


def test_validate_attachment_upload_rejects_pdf_without_real_signature() -> None:
    fake = b"this is not a real pdf despite the extension"
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=fake, filename="doc.pdf", declared_content_type="application/pdf"
        )


def test_validate_attachment_upload_accepts_a_real_docx_zip_signature() -> None:
    data = b"PK\x03\x04" + b"\x00" * 20
    result = validate_attachment_upload(
        data=data,
        filename="doc.docx",
        declared_content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert "wordprocessingml" in result.mime_type


def test_validate_attachment_upload_rejects_docx_without_zip_signature() -> None:
    fake = b"not a zip container despite the .docx extension"
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=fake,
            filename="doc.docx",
            declared_content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


def test_validate_attachment_upload_accepts_valid_utf8_csv() -> None:
    data = b"name,quantity\nTomato,5\n"
    result = validate_attachment_upload(
        data=data, filename="stock.csv", declared_content_type="text/csv"
    )
    assert result.mime_type == "text/csv"


def test_validate_attachment_upload_rejects_binary_content_disguised_as_csv() -> None:
    # Binary content (null bytes) with a .csv extension — a common way to
    # smuggle an executable or other binary payload past a naive
    # extension-only check.
    fake = b"name,quantity\x00\x01\x02binary garbage"
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=fake, filename="stock.csv", declared_content_type="text/csv"
        )


def test_validate_attachment_upload_rejects_unsupported_extension() -> None:
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=b"MZ\x90\x00",
            filename="payload.exe",
            declared_content_type="application/octet-stream",
        )


def test_validate_attachment_upload_rejects_oversized_file() -> None:
    oversized = b"%PDF-1.4\n" + b"\x00" * (16 * 1024 * 1024)
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=oversized, filename="doc.pdf", declared_content_type="application/pdf"
        )


def test_validate_attachment_upload_rejects_image_signature_mismatch() -> None:
    fake = b"not a real jpeg despite the extension and declared content type"
    with pytest.raises(AttachmentValidationError):
        validate_attachment_upload(
            data=fake, filename="photo.jpg", declared_content_type="image/jpeg"
        )
