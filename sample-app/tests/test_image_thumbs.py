import io
import unittest

from PIL import Image, features

from app.image_thumbs import THUMB_SIZE, make_thumbnail


def _encode(fmt: str, size=(800, 600), mode="RGB") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, "red").save(buf, format=fmt)
    return buf.getvalue()


class MakeThumbnailTest(unittest.TestCase):
    def assert_valid_thumb(self, data: bytes):
        with Image.open(io.BytesIO(data)) as thumb:
            self.assertEqual(thumb.format, "PNG")
            self.assertLessEqual(thumb.size[0], THUMB_SIZE[0])
            self.assertLessEqual(thumb.size[1], THUMB_SIZE[1])
            self.assertEqual(thumb.mode, "RGBA")

    def test_png_upload(self):
        self.assert_valid_thumb(make_thumbnail(_encode("PNG")))

    def test_jpeg_upload(self):
        self.assert_valid_thumb(make_thumbnail(_encode("JPEG")))

    @unittest.skipUnless(features.check("webp"), "Pillow built without WebP")
    def test_webp_upload(self):
        # WebP decode is the path the libwebp CVE fix touches.
        self.assert_valid_thumb(make_thumbnail(_encode("WEBP")))

    def test_aspect_ratio_preserved(self):
        with Image.open(io.BytesIO(make_thumbnail(_encode("PNG", size=(800, 400))))) as thumb:
            self.assertEqual(thumb.size, (256, 128))

    def test_garbage_bytes_rejected(self):
        with self.assertRaises(Exception):
            make_thumbnail(b"not an image")


if __name__ == "__main__":
    unittest.main()
