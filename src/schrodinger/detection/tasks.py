import time
from datetime import datetime
import pickle
import uuid

import cv2
from celery.utils.log import get_task_logger
import redis

from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, EntityDetector
from schrodinger.models import Event
from schrodinger.worker.redis import RedisTask
from schrodinger.worker.s3 import S3ServiceTask
from schrodinger.worker.sqlalchemy import SQLAlachemyTask

logger = get_task_logger("test")


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


class DatabaseTask(SQLAlachemyTask, S3ServiceTask, RedisTask):
    pass


@celery.task(name="detect_object", base=DatabaseTask, bind=True)
def detect_object(self):
    entity_detector = EntityDetector()

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
                        if (
                            entity := entity_detector.process_inference_results(
                                results, CocoClassId.cup
                            )
                        ) is not None:
                            annotated_frame = annotate_frame(
                                frame, entity.box, entity.name, entity.confidence
                            )

                            # cv2.imwrite(
                            #     f"{output_dir}/{timestamp:.6f}.png", annotated_frame
                            # )

                            detection_key = f"detection:{timestamp:.6f}"
                            detection_data = {
                                "timestamp": timestamp,
                                "object": entity.name,
                                "confidence": entity.confidence,
                                "box": entity.box.xyxy[0].tolist(),
                            }
                            self.redis.setex(
                                detection_key, 3600, pickle.dumps(detection_data)
                            )

                            print(
                                f"Detected {entity.name} with confidence {entity.confidence:.2f} at {datetime.fromtimestamp(timestamp)}"
                            )

                            frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
                            frame_s3_key = (
                                f"{uuid.uuid4()}/{entity.name}_entered_{timestamp}.png"
                            )
                            self.s3_service.upload(
                                frame_bytes, frame_s3_key, mime_type="image/png"
                            )

                            annotated_frame_bytes = cv2.imencode(
                                ".png", annotated_frame
                            )[1].tobytes()
                            annotated_frame_s3_key = f"{uuid.uuid4()}/annotated_{entity.name}_entered_{timestamp}.png"
                            self.s3_service.upload(
                                annotated_frame_bytes,
                                annotated_frame_s3_key,
                                mime_type="image/png",
                            )

                            # Create event using sync session
                            with self.session_maker() as session:
                                event = Event(
                                    entity_id=entity.class_id,
                                    name=entity.name,
                                    timestamp=datetime.fromtimestamp(timestamp),
                                    start_time=datetime.fromtimestamp(timestamp),
                                    s3_key=annotated_frame_s3_key,
                                )
                                session.add(event)
                                session.commit()

                    except Exception as e:
                        print(f"Error processing frame: {e}")
                    finally:
                        self.redis.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

        except Exception as e:
            print(f"Error reading from stream: {e}")
            time.sleep(1)
