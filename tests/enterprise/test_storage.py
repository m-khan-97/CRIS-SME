import io
from uuid import uuid4

from botocore.exceptions import ClientError
import boto3
from botocore.stub import Stubber, ANY
import pytest

from cris_sme.enterprise.storage import LocalStorage, S3Storage, configured_storage

KEY = f"{uuid4()}/{uuid4()}/reports/cris_sme_report.json"


class MemoryS3:
    """Transport fixture, not an AWS or S3-compatible-server qualification."""
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.public = False
        self.versioning = True
        self.fail = False

    def get_public_access_block(self, **kwargs):
        return {"PublicAccessBlockConfiguration": {key: not self.public for key in (
            "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")}}

    def get_bucket_versioning(self, **kwargs):
        return {"Status": "Enabled" if self.versioning else "Suspended"}

    def list_object_versions(self, **kwargs):
        return {"Versions": [{"Key": key} for key in self.objects if key.startswith(kwargs["Prefix"])][:1]}

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")
        if kwargs["Key"] in self.objects:
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {"VersionId": "fixture-version"}

    def get_object(self, **kwargs):
        raw = self.objects[kwargs["Key"]]
        return {"Body": io.BytesIO(raw), "ContentLength": len(raw)}


def remote():
    return S3Storage(MemoryS3(), "cris-fixture-bucket", "private-deployment/artifacts")


def test_conditional_writes_and_readback_match_real_sdk_contract():
    client = boto3.client("s3", region_name="eu-west-2", aws_access_key_id="fixture", aws_secret_access_key="fixture")
    storage = S3Storage(client, "cris-fixture-bucket", "private")
    with Stubber(client) as stub:
        stub.add_response("get_public_access_block", {"PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True}},
            {"Bucket": "cris-fixture-bucket"})
        stub.add_response("get_bucket_versioning", {"Status": "Enabled"}, {"Bucket": "cris-fixture-bucket"})
        stub.add_response("put_object", {"VersionId": "fixture"}, {"Bucket": "cris-fixture-bucket", "Key": "private/" + KEY,
            "Body": b"original", "ContentLength": 8, "ContentType": "application/octet-stream",
            "ServerSideEncryption": "AES256", "ChecksumSHA256": ANY, "IfNoneMatch": "*"})
        stub.add_response("get_object", {"Body": io.BytesIO(b"original"), "ContentLength": 8},
                          {"Bucket": "cris-fixture-bucket", "Key": "private/" + KEY})
        storage.publish(KEY, b"original")
        stub.assert_no_pending_responses()


def test_idempotence_conflict_and_private_bucket_requirements():
    storage = remote()
    storage.check_ready()
    storage.require_empty()
    storage.publish(KEY, b"original")
    storage.publish(KEY, b"original")
    with pytest.raises(ValueError, match="never overwritten"):
        storage.publish(KEY, b"changed")
    assert storage.read(KEY) == b"original"
    with pytest.raises(ValueError, match="unused S3"):
        storage.require_empty()
    storage.client.list_object_versions = lambda **kwargs: {"DeleteMarkers": [{"Key": KEY}]}
    with pytest.raises(ValueError, match="unused S3"):
        storage.require_empty()
    storage.client.public = True
    with pytest.raises(ValueError, match="public access"):
        storage.check_ready()
    storage.client.public = False
    storage.client.versioning = False
    with pytest.raises(ValueError, match="versioning"):
        storage.check_ready()
    storage.client.versioning = True
    storage.client.fail = True
    with pytest.raises(ClientError):
        storage.publish(KEY, b"original")


@pytest.mark.parametrize("key", ["../escape", "/absolute", "tenant/job/report", KEY.replace("/reports/", "//reports/"),
                                  KEY.replace("/reports/", "/../"), KEY + "/.hidden", KEY + "\\escape"])
def test_invalid_object_namespaces_fail_before_network(key):
    storage = remote()
    with pytest.raises(ValueError):
        storage.publish(key, b"fixture")
    assert storage.client.calls == []


@pytest.mark.parametrize("bucket,prefix", [("../bucket", "safe"), ("127.0.0.1", "safe"), ("safe-bucket", ""),
                                         ("safe-bucket", "/root"), ("safe-bucket", "a/../b"), ("safe-bucket", "a//b")])
def test_bucket_and_prefix_configuration_rejected(bucket, prefix):
    with pytest.raises(ValueError):
        S3Storage(MemoryS3(), bucket, prefix)


@pytest.mark.parametrize("length,raw,limit", [(33, b"small", 32), (4, b"short", 32), (-1, b"", 32), (True, b"x", 32), (0, b"", 0)])
def test_remote_reads_are_bounded_and_always_close_body(length, raw, limit):
    storage = remote()
    stream = io.BytesIO(raw)
    storage.client.get_object = lambda **kwargs: {"Body": stream, "ContentLength": length}
    with pytest.raises(ValueError):
        storage.read(KEY, max_bytes=limit)
    if limit:
        assert stream.closed


def test_local_transport_remains_anchored_and_never_replaces_content(tmp_path):
    path = tmp_path / "report"
    path.write_bytes(b"original")
    storage = LocalStorage(tmp_path)
    storage.check_ready()
    storage.publish("report", b"original")
    with pytest.raises(ValueError):
        storage.publish("report", b"changed")
    assert path.read_bytes() == b"original"
    path.unlink()
    path.symlink_to("/etc/passwd")
    with pytest.raises(OSError):
        storage.read("report")


def test_factory_defaults_local_and_configures_fixed_tls_sdk(monkeypatch, tmp_path):
    assert isinstance(configured_storage(tmp_path, {}), LocalStorage)
    with pytest.raises(ValueError):
        configured_storage(tmp_path, {"CRIS_ENTERPRISE_STORAGE_BACKEND": "unknown"})
    env = {"CRIS_ENTERPRISE_STORAGE_BACKEND": "s3", "CRIS_ENTERPRISE_S3_REGION": "eu-west-2",
           "CRIS_ENTERPRISE_S3_BUCKET": "safe-bucket", "CRIS_ENTERPRISE_S3_PREFIX": "private"}
    calls = []
    class Session:
        def client(self, service, **kwargs):
            calls.append((service, kwargs))
            return MemoryS3()
    monkeypatch.setattr(boto3, "Session", Session)
    storage = configured_storage(tmp_path, env)
    assert isinstance(storage, S3Storage)
    assert calls == []
    storage.check_ready()
    service, options = calls[0]
    assert service == "s3" and options["use_ssl"] is True
    assert options["config"].ignore_configured_endpoint_urls is True
    with pytest.raises(ValueError):
        configured_storage(tmp_path, {**env, "CRIS_ENTERPRISE_S3_REGION": "http://metadata/"})
