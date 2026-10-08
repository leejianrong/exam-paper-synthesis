"""Importable image-byte builders for asset tests (not a test module)."""

from __future__ import annotations

import struct
import zlib


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def png(width: int = 2, height: int = 3) -> bytes:
    """A real, decodable RGB PNG of the given size (solid colour)."""
    raw = b"".join(b"\x00" + b"\xff\x80\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def jpeg(width: int = 4, height: int = 5) -> bytes:
    """A structurally valid JPEG (SOI, APP0, SOF0 with the size, SOS, EOI).

    Not decodable pixel data — the upload gate reads headers only, as does this test.
    """
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = b"\xff\xc0\x00\x0b\x08" + struct.pack(">HH", height, width) + b"\x01\x01\x11\x00"
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    return b"\xff\xd8" + app0 + sof0 + sos + b"\x00\x01\x02" + b"\xff\xd9"
