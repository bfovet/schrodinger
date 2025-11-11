from datetime import datetime

from schrodinger_server.kit.schemas import IDSchema, Schema


def get_downloadable_content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"'


class S3UploadURL(Schema):
    url: str
    headers: dict[str, str] = {}
    expires_at: datetime


class S3FileCreate(Schema):
    name: str
    mime_type: str
    size: int

    checksum_sha256_base64: str | None = None

    upload: S3UploadURL


class S3File(IDSchema, validate_assignment=True):
    name: str
    path: str
    mime_type: str
    size: int

    # Provided by AWS S3
    storage_version: str | None
    checksum_etag: str | None

    # Provided by us
    checksum_sha256_base64: str | None
    checksum_sha256_hex: str | None

    last_modified_at: datetime | None


class S3DownloadURL(Schema):
    url: str
    headers: dict[str, str] = {}
    expires_at: datetime


class S3FileDownload(S3File):
    download: S3DownloadURL
