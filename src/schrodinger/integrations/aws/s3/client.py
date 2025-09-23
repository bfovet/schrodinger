from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

if TYPE_CHECKING:
    from types_boto3_s3.client import S3Client


def get_client(*, signature_version: str = "v4") -> "S3Client":
    return boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minio_user",
        aws_secret_access_key="minioadmin123",
        config=Config(
            signature_version=signature_version, s3={"addressing_style": "path"}
        ),
    )


client = get_client()
