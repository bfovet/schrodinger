from schrodinger.kit.schemas import Schema


class ReadinessSchema(Schema):
    postgres: bool
    redis: bool
    minio: bool
    celery: bool
