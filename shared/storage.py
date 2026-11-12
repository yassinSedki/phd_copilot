"""File storage behind one interface: local disk for dev, Azure Blob in the cloud.

Callers only ever do `get_storage().save(key, data)` and persist the returned
location string; they never know which backend is active. Keys are
forward-slash paths such as "cvs/user_3/ab12cd34.pdf".

Why a bucket in the cloud: a pod's local disk disappears when the pod is
replaced (rollout, scale-down, node loss), and a ReadWriteOnce volume can't be
mounted by pods on different nodes. Blob storage is durable and reachable
from every replica.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Protocol

from shared.config import get_settings


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> str:
        """Store `data` under `key`; return a location string to persist."""
        ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, key: str, data: bytes) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)


class AzureBlobStorage:
    def __init__(self, account_url: str, container: str) -> None:
        if not account_url:
            raise RuntimeError("FILE_STORE__BACKEND=azure requires FILE_STORE__AZURE_ACCOUNT_URL")
        # Lazy imports: the Azure SDKs are only needed when this backend is on.
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        # DefaultAzureCredential resolves to the pod's workload identity on
        # AKS, or to your `az login` session on a laptop. No keys anywhere.
        service = BlobServiceClient(account_url, credential=DefaultAzureCredential())
        self._container = service.get_container_client(container)
        self._name = container

    def save(self, key: str, data: bytes) -> str:
        self._container.upload_blob(key, data, overwrite=True)
        return f"azure://{self._name}/{key}"


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    settings = get_settings()
    backend = settings.file_store.backend.lower()
    if backend == "azure":
        return AzureBlobStorage(settings.file_store.azure_account_url, settings.file_store.azure_container)
    if backend == "local":
        return LocalStorage(settings.storage_dir)
    raise RuntimeError(f"Unknown FILE_STORE__BACKEND {backend!r} (expected 'local' or 'azure')")
