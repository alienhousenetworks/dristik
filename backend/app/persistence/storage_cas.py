"""
Content-Addressable Storage (CAS) Service for DOM Snapshots, HAR files, and Evidence Artifacts.
Supports local filesystem CAS with SHA-256 addressing and S3/R2 cloud storage abstraction.
"""
import hashlib
import os
from pathlib import Path
from typing import Optional, Union, Tuple


class ContentAddressableStorage:
    def __init__(self, base_dir: str = "data/cas"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # S3 / R2 configuration
        self.s3_bucket = os.getenv("DRISTIK_CAS_S3_BUCKET")
        self.s3_endpoint = os.getenv("DRISTIK_CAS_S3_ENDPOINT")
        self.s3_access_key = os.getenv("DRISTIK_CAS_S3_ACCESS_KEY")
        self.s3_secret_key = os.getenv("DRISTIK_CAS_S3_SECRET_KEY")

    def _hash_content(self, data: Union[bytes, str]) -> Tuple[str, bytes]:
        raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        return content_hash, raw_bytes

    def put(self, data: Union[bytes, str], extension: str = "raw") -> Tuple[str, str]:
        """
        Stores content addressed by its SHA-256 hash.
        Returns:
            (content_hash, storage_uri) e.g. ("a1b2...", "cas://a1b2.../data.raw")
        """
        content_hash, raw_bytes = self._hash_content(data)
        # Sharded prefix directory: data/cas/ab/cd/<hash>.<ext>
        prefix = content_hash[:2]
        shard_dir = self.base_dir / prefix
        shard_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{content_hash}.{extension.lstrip('.')}"
        target_path = shard_dir / file_name

        if not target_path.exists():
            # Atomic write via temporary file
            temp_path = target_path.with_suffix(".tmp")
            with open(temp_path, "wb") as f:
                f.write(raw_bytes)
            temp_path.replace(target_path)

        storage_uri = f"cas://{content_hash}/{file_name}"
        return content_hash, storage_uri

    def get(self, content_hash_or_uri: str) -> Optional[bytes]:
        """
        Retrieves raw bytes by content hash or storage_uri.
        """
        clean_hash = content_hash_or_uri.replace("cas://", "").split("/")[0].split(".")[0]
        prefix = clean_hash[:2]
        shard_dir = self.base_dir / prefix
        
        if not shard_dir.exists():
            return None

        for match in shard_dir.glob(f"{clean_hash}.*"):
            if not match.name.endswith(".tmp"):
                with open(match, "rb") as f:
                    return f.read()
        return None

    def exists(self, content_hash_or_uri: str) -> bool:
        clean_hash = content_hash_or_uri.replace("cas://", "").split("/")[0].split(".")[0]
        prefix = clean_hash[:2]
        shard_dir = self.base_dir / prefix
        if not shard_dir.exists():
            return False
        return any(not m.name.endswith(".tmp") for m in shard_dir.glob(f"{clean_hash}.*"))


_global_cas: Optional[ContentAddressableStorage] = None


def get_cas_storage() -> ContentAddressableStorage:
    global _global_cas
    if _global_cas is None:
        _global_cas = ContentAddressableStorage()
    return _global_cas
