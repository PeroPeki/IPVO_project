"""
Upload slika — Cloudinary (produkcija/MVP) ili lokalni disk (razvoj bez ključa).

Ako je CLOUDINARY_URL postavljen, slika ide na Cloudinary CDN i vraća se
secure_url. Inače se sprema u /app/uploads i servira kroz /api/uploads/.
"""

import os
import uuid

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def _extension(filename):
    if "." not in (filename or ""):
        return None
    ext = filename.rsplit(".", 1)[1].lower()
    return ext if ext in ALLOWED_EXTENSIONS else None


def save_image(file_storage, folder="misc"):
    """Sprema sliku i vraća javni URL. Podiže ValueError za nepodržani format."""
    ext = _extension(file_storage.filename)
    if not ext:
        raise ValueError("Nepodržani format slike (dozvoljeno: png, jpg, jpeg, webp, gif)")

    if os.environ.get("CLOUDINARY_URL"):
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file_storage, folder=f"nightclub/{folder}"
        )
        return result["secure_url"]

    target_dir = os.path.join(UPLOAD_DIR, folder)
    os.makedirs(target_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(target_dir, name))
    return f"/api/uploads/{folder}/{name}"
