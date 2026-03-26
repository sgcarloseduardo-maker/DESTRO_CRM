import json
from pathlib import Path

from image_manager import (
    build_image_index,
    load_metadata,
    normalize_product_code,
    store_product_image,
)


class DummyUpload:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content
        self.size = len(content)

    def getbuffer(self):
        return self._content


def test_normalize_product_code():
    assert normalize_product_code("12345-7") == "123457"
    assert normalize_product_code("ABC00123") == "00123"
    assert normalize_product_code("") == ""


def test_store_product_image_invalid_code(tmp_path: Path):
    upload = DummyUpload("img.jpg", b"abc")
    ok, msg, _ = store_product_image(
        base_dir=str(tmp_path),
        uploaded_file=upload,
        code="abc",
        allowed_exts={".jpg", ".png"},
        max_mb=1,
    )
    assert ok is False
    assert "Código do produto inválido" in msg


def test_store_product_image_success_and_metadata(tmp_path: Path):
    upload = DummyUpload("img.jpg", b"fake-image-content")
    ok, msg, meta = store_product_image(
        base_dir=str(tmp_path),
        uploaded_file=upload,
        code="123456",
        allowed_exts={".jpg", ".png"},
        max_mb=1,
    )
    assert ok is True
    assert "sucesso" in msg.lower()
    assert meta["code"] == "123456"
    assert "hash_sha256" in meta

    md = load_metadata(str(tmp_path))
    assert "123456" in md["images"]
    idx, _ = build_image_index(str(tmp_path))
    assert "123456" in idx


def test_store_product_image_replacement_creates_backup(tmp_path: Path):
    upload1 = DummyUpload("img.jpg", b"first")
    upload2 = DummyUpload("img.jpg", b"second")

    ok1, _, _ = store_product_image(
        base_dir=str(tmp_path),
        uploaded_file=upload1,
        code="777777",
        allowed_exts={".jpg", ".png"},
        max_mb=1,
    )
    assert ok1 is True

    ok2, _, meta2 = store_product_image(
        base_dir=str(tmp_path),
        uploaded_file=upload2,
        code="777777",
        allowed_exts={".jpg", ".png"},
        max_mb=1,
    )
    assert ok2 is True
    assert meta2["replaced_previous"] is True
    assert meta2["backup_path"] != ""
    assert Path(meta2["backup_path"]).exists()

    metadata_file = tmp_path / "Base de Imagens" / "image_metadata.json"
    data = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert "777777" in data["images"]
