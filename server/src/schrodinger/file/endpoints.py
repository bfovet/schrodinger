from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from schrodinger.config import settings
from schrodinger.integrations.aws.s3.service import S3Service

router = APIRouter(prefix="/files", tags=["files"])

s3_service = S3Service(bucket=settings.S3_FILES_BUCKET_NAME)


@router.get("/{path:path}", summary="Get File")
async def get_file(path: str) -> RedirectResponse:
    """
    Get a file from S3 by redirecting to a presigned URL.
    """
    presigned_url, _ = s3_service.generate_presigned_download_url(
        path=path,
        filename=path.split("/")[-1],
        mime_type="image/png",
    )
    return RedirectResponse(url=presigned_url)