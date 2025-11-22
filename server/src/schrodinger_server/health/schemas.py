from schrodinger_server.kit.schemas import Schema


class ReadinessSchema(Schema):
    minio: bool
    celery: bool
