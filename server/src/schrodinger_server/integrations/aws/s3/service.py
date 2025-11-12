from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from aiohttp import ClientError

from schrodinger_server.integrations.aws.s3.client import client
from schrodinger_server.integrations.aws.s3.exceptions import S3FileError
from schrodinger_server.integrations.aws.s3.schemas import \
    get_downloadable_content_disposition

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client
    from types_boto3_s3.type_defs import PutObjectRequestTypeDef


class S3Service:
    def __init__(self, bucket, presign_ttl: int = 600, client: "S3Client" = client):
        self.bucket = bucket
        self.presign_ttl = presign_ttl
        self.client = client

    def upload(
        self,
        data: bytes,
        path: str,
        mime_type: str,
        checksum_sha256_base64: str | None = None,
    ):
        """
        Uploads a file directly to S3.
        """
        request: PutObjectRequestTypeDef = {
            "Bucket": self.bucket,
            "Key": path,
            "Body": data,
            "ContentType": mime_type,
        }
        if checksum_sha256_base64 is not None:
            request["ChecksumAlgorithm"] = "SHA256"
            request["ChecksumSHA256"] = checksum_sha256_base64

        if checksum_sha256_base64:
            request["ChecksumSHA256"] = checksum_sha256_base64

        self.client.put_object(**request)
        return path

    def get_object_or_raise(self, path: str, s3_version_id: str = "") -> dict[str, Any]:
        try:
            obj = self.client.get_object(
                Bucket=self.bucket,
                Key=path,
                VersionId=s3_version_id,
                ChecksumMode="ENABLED",
            )
        except ClientError:
            raise S3FileError("No object on S3")

        return cast(dict[str, Any], obj)

    def generate_presigned_download_url(
        self,
        *,
        path: str,
        filename: str,
        mime_type: str,
    ) -> tuple[str, datetime]:
        expires_in = self.presign_ttl
        presign_from = datetime.now(UTC)
        signed_download_url = self.client.generate_presigned_url(
            "get_object",
            Params=dict(
                Bucket=self.bucket,
                Key=path,
                ResponseContentDisposition=get_downloadable_content_disposition(
                    filename
                ),
                ResponseContentType=mime_type,
            ),
            ExpiresIn=expires_in,
        )

        presign_expires_at = presign_from + timedelta(seconds=expires_in)
        return (signed_download_url, presign_expires_at)
