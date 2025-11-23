import json
import pickle
import time
import uuid
from datetime import datetime

import cv2
import numpy as np
from sqlalchemy.orm import Session
import redis
import structlog
from celery.utils.log import get_task_logger

from schrodinger_server.celery import celery
from schrodinger_server.detection.detection import CocoClassId, EntityDetector
from schrodinger_server.integrations.aws.s3.service import S3Service
from schrodinger_server.logging import Logger
from schrodinger_server.models import Event
from schrodinger_server.worker.redis import RedisTask
from schrodinger_server.worker.s3 import S3ServiceTask
from schrodinger_server.worker.sqlalchemy import SQLAlachemyTask

log: Logger = structlog.wrap_logger(get_task_logger(__name__))


STREAM_NAME = "frame_stream"
CONSUMER_GROUP = "detection_group"
CONSUMER_NAME = "detector_1"


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
    timestamp: str,
    event_name: str,
) -> str:
    frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
    frame_s3_key = f"{uuid.uuid4()}/{entity_name}_{event_name}_{timestamp}.png"
    s3_service.upload(frame_bytes, frame_s3_key, mime_type="image/png")

    return frame_s3_key


def register_event(
    entity_class_id: int,
    entity_name: str,
    event_type: str,
    timestamp: float,
    raw_frame_s3_key: str,
    annotated_frame_s3_key: str,
    session: Session,
):
    event = Event(
        entity_id=entity_class_id,
        name=entity_name,
        event_type=event_type,
        timestamp=datetime.fromtimestamp(timestamp),
        raw_frame_s3_key=raw_frame_s3_key,
        annotated_frame_s3_key=annotated_frame_s3_key,
    )
    session.add(event)
    session.commit()


class DatabaseTask(SQLAlachemyTask, S3ServiceTask, RedisTask):
    pass


@celery.task(name="detect_object", base=DatabaseTask, bind=True)
def detect_object(self):
    entity_detector = EntityDetector()

    entity_found_before = False
    entity_found = False

    latest_raw_frame_with_entity_found: np.ndarray | None = None
    latest_annotated_frame_with_entity_found: np.ndarray | None = None

    try:
        self.redis.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    last_id = ">"

    while True:
        try:
            messages = self.redis.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                {STREAM_NAME: last_id},
                count=1,
                block=100,
            )

            if not messages:
                continue

            for _, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    try:
                        frame_data = pickle.loads(message_data[b"frame_data"])
                        timestamp = frame_data["timestamp"]
                        frame = frame_data["frame"]

                        results = entity_detector.run_inference(frame)
                        entity = entity_detector.process_inference_results(
                            results, CocoClassId.cup
                        )
                        if entity is not None:
                            annotated_frame = annotate_frame(
                                frame, entity.box, entity.name, entity.confidence
                            )

                            entity_found = True
                            latest_raw_frame_with_entity_found = frame
                            latest_annotated_frame_with_entity_found = annotated_frame

                            entity_key = entity.name
                            entity_data = {
                                "confidence": entity.confidence,
                                "class_id": entity.class_id,
                            }
                            self.redis.set(entity_key, json.dumps(entity_data))
                        else:
                            entity_found = False

                        if not entity_found_before and entity_found:
                            event_name = "entered"
                            log.info(f"Entity {event_name} frame",
                                     entity_name=entity.name,
                                     event_name=event_name,
                                     confidence=f"{entity.confidence:.2f}",
                                     datetime=f"{datetime.fromtimestamp(timestamp)}")
                            entity_found_before = True

                            raw_frame_s3_key = upload_frame_to_s3(
                                self.s3_service,
                                latest_raw_frame_with_entity_found,
                                entity.name,
                                timestamp,
                                event_name,
                            )
                            annotated_frame_s3_key = upload_frame_to_s3(
                                self.s3_service,
                                latest_annotated_frame_with_entity_found,
                                entity.name,
                                timestamp,
                                event_name,
                            )

                            with self.session_maker() as session:
                                register_event(
                                    entity.class_id,
                                    entity.name,
                                    event_name,
                                    timestamp,
                                    raw_frame_s3_key,
                                    annotated_frame_s3_key,
                                    session,
                                )
                        if entity_found_before and not entity_found:
                            entity_name = "cup"
                            entity_str = self.redis.getdel(entity_name)
                            if entity_str:
                                entity_dict = json.loads(entity_str)

                            entity_class_id = entity_dict["class_id"]
                            entity_confidence = entity_dict["confidence"]

                            event_name = "left"
                            log.info(f"Entity {event_name} frame",
                                     entity_name=entity_name,
                                     confidence=f"{entity_confidence:.2f}",
                                     datetime=f"{datetime.fromtimestamp(timestamp)}")
                            entity_found_before = False

                            raw_frame_s3_key = upload_frame_to_s3(
                                self.s3_service,
                                latest_raw_frame_with_entity_found,
                                entity_name,
                                timestamp,
                                event_name,
                            )
                            annotated_frame_s3_key = upload_frame_to_s3(
                                self.s3_service,
                                latest_annotated_frame_with_entity_found,
                                entity_name,
                                timestamp,
                                event_name,
                            )

                            with self.session_maker() as session:
                                register_event(
                                    entity_class_id,
                                    entity_name,
                                    event_name,
                                    timestamp,
                                    raw_frame_s3_key,
                                    annotated_frame_s3_key,
                                    session,
                                )

                    except Exception as e:
                        log.error("Error processing frame", error=e)
                    finally:
                        self.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

        except Exception as e:
            log.error("Error reading from stream", error=e)
            time.sleep(1)
