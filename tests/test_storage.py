"""File store abstraction (shared/storage.py)."""

from pathlib import Path

from shared.storage import LocalStorage


def test_local_storage_writes_nested_key(tmp_path: Path):
    location = LocalStorage(tmp_path).save("cvs/user_1/abc.pdf", b"%PDF-1.4")

    assert Path(location) == tmp_path / "cvs" / "user_1" / "abc.pdf"
    assert Path(location).read_bytes() == b"%PDF-1.4"


def test_local_storage_overwrites_same_key(tmp_path: Path):
    store = LocalStorage(tmp_path)
    store.save("raw/x.txt", b"old")
    location = store.save("raw/x.txt", b"new")

    assert Path(location).read_bytes() == b"new"
