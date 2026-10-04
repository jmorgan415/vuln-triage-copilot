"""Avatar thumbnail generation for customer profile uploads."""
import io

from PIL import Image

THUMB_SIZE = (256, 256)
# Upload size cap is enforced at the API gateway, not here.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def make_thumbnail(image_bytes: bytes, out_format: str = "PNG") -> bytes:
    """Produce a square thumbnail from a customer-uploaded avatar."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGBA")
        img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format=out_format)
        return buf.getvalue()
