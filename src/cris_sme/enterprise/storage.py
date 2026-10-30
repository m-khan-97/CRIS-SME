"""Private artifact transport. Tenant authorization remains the metadata store's job."""
import base64
import hashlib
import os
from pathlib import Path
import re
from typing import Protocol
from uuid import UUID

from cris_sme.api.artifact_access import MAX_ARTIFACT_BYTES, read_regular_file


class ArtifactStorage(Protocol):
    def read(self, key: str, *, max_bytes: int = MAX_ARTIFACT_BYTES) -> bytes: ...
    def publish(self, key: str, content: bytes) -> None: ...
    def check_ready(self) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root

    def read(self, key, *, max_bytes=MAX_ARTIFACT_BYTES):
        return read_regular_file(self.root, Path(key), max_bytes=max_bytes)

    def publish(self, key, content):
        # Local writers already stage in their unique namespace. Never overwrite.
        if self.read(key) != content:
            raise ValueError("Local publication integrity check failed")

    def check_ready(self):
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("Private artifact directory is unavailable")


class S3Storage:
    def __init__(self, client, bucket: str, prefix: str, *, client_factory=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) or ".." in bucket or re.fullmatch(r"[0-9.]+", bucket):
            raise ValueError("Configure a general-purpose S3 bucket name")
        if len(prefix) > 100 or not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", prefix):
            raise ValueError("Configure a dedicated S3 deployment prefix")
        self._client, self._client_factory = client, client_factory
        self.bucket, self.prefix = bucket, prefix

    @property
    def client(self):
        if self._client is None:
            if self._client_factory is None:
                raise ValueError("S3 client is not configured")
            self._client = self._client_factory()
        return self._client

    def _key(self, key):
        path = Path(key)
        if path.is_absolute() or str(path) != key or len(path.parts) < 3 or len(key.encode()) > 900:
            raise ValueError("Invalid object namespace")
        if any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part) for part in path.parts):
            raise ValueError("Invalid object namespace")
        if any(str(UUID(part)) != part for part in path.parts[:2]):
            raise ValueError("Object keys require canonical tenant and job UUIDs")
        return self.prefix + "/" + key

    def check_ready(self):
        block = self.client.get_public_access_block(Bucket=self.bucket)["PublicAccessBlockConfiguration"]
        if any(block.get(key) is not True for key in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")):
            raise ValueError("S3 public access blocking must be fully enabled")
        if self.client.get_bucket_versioning(Bucket=self.bucket).get("Status") != "Enabled":
            raise ValueError("S3 versioning must be enabled")

    def require_empty(self):
        result = self.client.list_object_versions(Bucket=self.bucket, Prefix=self.prefix + "/", MaxKeys=1)
        if result.get("Versions") or result.get("DeleteMarkers") or result.get("IsTruncated"):
            raise ValueError("Restore requires an unused S3 deployment prefix")

    def read(self, key, *, max_bytes=MAX_ARTIFACT_BYTES):
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_ARTIFACT_BYTES:
            raise ValueError("Invalid object read limit")
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        body = response["Body"]
        try:
            length = response["ContentLength"]
            if isinstance(length, bool) or not isinstance(length, int) or not 0 <= length <= max_bytes:
                raise ValueError("Object exceeds read limit")
            content = body.read(max_bytes + 1)
            if len(content) != length or len(content) > max_bytes:
                raise ValueError("Object length mismatch")
            return content
        finally:
            body.close()

    def publish(self, key, content):
        from botocore.exceptions import ClientError
        if not isinstance(content, bytes) or len(content) > MAX_ARTIFACT_BYTES:
            raise ValueError("Invalid object publication size")
        object_key = self._key(key)
        self.check_ready()
        try:
            self.client.put_object(Bucket=self.bucket, Key=object_key, Body=content,
                ContentLength=len(content), ContentType="application/octet-stream", ServerSideEncryption="AES256",
                ChecksumSHA256=base64.b64encode(hashlib.sha256(content).digest()).decode(), IfNoneMatch="*")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"PreconditionFailed", "412"}:
                raise
        if self.read(key) != content:
            raise ValueError("Object publication integrity check failed; existing content is never overwritten")


def configured_storage(root: Path, env=None) -> ArtifactStorage:
    env = os.environ if env is None else env
    backend = env.get("CRIS_ENTERPRISE_STORAGE_BACKEND", "local")
    if backend == "local":
        return LocalStorage(root)
    if backend != "s3":
        raise ValueError("Unsupported artifact storage backend")
    region = env.get("CRIS_ENTERPRISE_S3_REGION", "")
    if not re.fullmatch(r"(?:us|eu|ap|sa|ca|me|af|il|mx)-[a-z]+-[0-9]+", region):
        raise ValueError("Configure a commercial AWS region for S3 storage")
    def client_factory():
        import boto3
        from botocore.config import Config
        return boto3.Session().client("s3", region_name=region, use_ssl=True,
            config=Config(connect_timeout=3, read_timeout=10, retries={"max_attempts": 1},
                          ignore_configured_endpoint_urls=True, max_pool_connections=4))
    return S3Storage(None, env.get("CRIS_ENTERPRISE_S3_BUCKET", ""),
                     env.get("CRIS_ENTERPRISE_S3_PREFIX", ""), client_factory=client_factory)
