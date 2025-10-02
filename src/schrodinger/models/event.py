from datetime import UTC, datetime
import uuid
from sqlalchemy import UUID, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class EntityDetectedEvent(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    s3_presigned_download_url: Mapped[str] = mapped_column(String(500), nullable=True)
