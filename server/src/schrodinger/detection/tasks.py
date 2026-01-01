import pickle
import time
import uuid
from datetime import datetime

import cv2
import numpy as np
import structlog
from celery.utils.log import get_task_logger

from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, DetectedEntity, EntityDetector
from schrodinger.integrations.aws.s3.service import S3Service
from schrodinger.logging import Logger
from schrodinger.models import Event
from schrodinger.redis import STREAM_NAME
from schrodinger.worker.redis import RedisTask
from schrodinger.worker.s3 import S3ServiceTask
from schrodinger.worker.sqlalchemy import SQLAlchemyTask

log: Logger = structlog.wrap_logger(get_task_logger(__name__))


def annotate_frame(frame, box, object_name, confidence):
    annotated_frame = frame.copy()
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    label = f"{object_name}: {confidence:.2f}"
    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cv2.rectangle(
        annotated_frame,
        (x1, y1 - label_size[1] - 10),
        (x1 + label_size[0], y1),
        (0, 255, 0),
        -1,
    )
    cv2.putText(
        annotated_frame,
        label,
        (x1, y1 - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        2,
    )

    return annotated_frame


def upload_frame_to_s3(
    s3_service: S3Service,
    frame: np.ndarray,
    entity_name: str,
    timestamp: float,
    event_name: str,
) -> str:
    frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
    frame_s3_key = f"{uuid.uuid4()}/{entity_name}_{event_name}_{timestamp}.png"
    s3_service.upload(frame_bytes, frame_s3_key, mime_type="image/png")

    return frame_s3_key


def save_event(
    self,
    event_name: str,
    timestamp: float,
    raw_frame: np.ndarray | None,
    annotated_frame: np.ndarray | None,
    entity: DetectedEntity,
):
    datetime_str = datetime.fromtimestamp(timestamp)
    log.info(
        f"Entity {entity.name} {event_name}",
        entity_name=entity.name,
        event_name=event_name,
        confidence=f"{entity.confidence:.2f}",
        datetime=datetime_str,
    )

    def _upload_to_s3(frame: np.ndarray) -> str:
        return upload_frame_to_s3(
            self.s3_service,
            frame,
            entity.name,
            timestamp,
            event_name,
        )

    event = Event(
        entity_id=entity.class_id,
        name=entity.name,
        event_type=event_name,
        timestamp=datetime_str,
        raw_frame_s3_key=_upload_to_s3(raw_frame) if raw_frame is not None else None,
        annotated_frame_s3_key=_upload_to_s3(annotated_frame)
        if annotated_frame is not None
        else None,
    )

    with self.session_maker() as session:
        session.add(event)
        session.commit()


class DatabaseTask(SQLAlchemyTask, S3ServiceTask, RedisTask):
    pass


@celery.task(name="detect_object", base=DatabaseTask, bind=True)
def detect_object(self):
    entity_to_detect = CocoClassId.cup
    entity_detector = EntityDetector()

    def get_frame(frame_key: str) -> np.ndarray | None:
        if (frame_pkl := self.redis.get(frame_key)) is not None:
            return pickle.loads(frame_pkl)
        return None

    while True:
        try:
            if (
                response := self.redis.xread({STREAM_NAME: "$"}, count=1, block=100)
            ) is not None:
                for message in response:
                    for _, message_data in message[1]:
                        try:
                            raw_frame = pickle.loads(message_data[b"frame"])
                            timestamp = float(message_data[b"timestamp"].decode())

                            results = entity_detector.run_inference(raw_frame)
                            if (
                                entity := entity_detector.process_inference_results(
                                    results, entity_to_detect
                                )
                            ) is not None:
                                if self.redis.get(entity.name) is not None:
                                    log.debug(
                                        "Entity was already in frame",
                                        timestamp=timestamp,
                                    )
                                    break

                                self.redis.set(entity.name, pickle.dumps(entity))

                                annotated_frame = annotate_frame(
                                    raw_frame,
                                    entity.box,
                                    entity.name,
                                    entity.confidence,
                                )

                                self.redis.set("raw_frame", pickle.dumps(raw_frame))
                                self.redis.set(
                                    "annotated_frame", pickle.dumps(annotated_frame)
                                )

                                save_event(
                                    self,
                                    "entered",
                                    timestamp,
                                    raw_frame,
                                    annotated_frame,
                                    entity=entity,
                                )
                            else:
                                log.debug(
                                    "Entity not detected",
                                    timestamp=timestamp,
                                )
                                if (
                                    entity_pkl := self.redis.getdel(
                                        entity_to_detect.name
                                    )
                                ) is not None:
                                    # entity was in frame but not anymore
                                    entity = pickle.loads(entity_pkl)
                                    raw_frame = get_frame("raw_frame")
                                    annotated_frame = get_frame("annotated_frame")
                                    save_event(
                                        self,
                                        "left",
                                        timestamp,
                                        raw_frame,
                                        annotated_frame,
                                        entity=entity,
                                    )

                        except Exception as e:
                            log.error("Error processing frame", error=e)
        except Exception as e:
            log.error("Error reading from stream", error=e)
            time.sleep(1)
