from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from schrodinger_server.config import settings

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client


def get_client(*, signature_version: str = "v4") -> "S3Client":
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.MINIO_USER,
        aws_secret_access_key=settings.MINIO_PWD,
        config=Config(
            signature_version=signature_version, s3={"addressing_style": "path"}
        ),
    )


client = get_client()
