import os
import time
from datetime import datetime
import pickle
import uuid

import cv2
from celery.utils.log import get_task_logger
from redis import Redis
import redis

from schrodinger.config import settings
from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, EntityDetector
from schrodinger.integrations.aws.s3.service import S3Service
from schrodinger.kit.db.postgres import create_sync_sessionmaker
from schrodinger.models import Event
from schrodinger.postgres import create_sync_engine
# from schrodinger.worker._sqlalchemy import DatabaseTask

# SCHRODINGER_RTSP_USERNAME = os.environ.get("USERNAME")
# SCHRODINGER_RTSP_PASSWORD = os.environ.get("PASSWORD")
# SCHRODINGER_RTSP_HOST_IP_ADDRESS = os.environ.get("HOST_IP_ADDRESS")
# SCHRODINGER_RTSP_STREAM_NAME = os.environ.get("STREAM_NAME")

logger = get_task_logger("test")

redis_client = Redis(
    settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
)


STREAM_NAME = "frame_stream"
CONSUMER_GROUP = "detection_group"
CONSUMER_NAME = "detector_1"


class DetectionTask(celery.Task):
    _s3_service = None
    _session_maker = None

    @property
    def s3_service(self):
        if self._s3_service is None:
            self._s3_service = S3Service(settings.S3_FILES_BUCKET_NAME)
        return self._s3_service

    @property
    def session_maker(self):
        if self._session_maker is None:
            sync_engine = create_sync_engine("worker")
            self._session_maker = create_sync_sessionmaker(sync_engine)
        return self._session_maker


# @celery.task(pydantic=True)
# def detect(entity_to_detect: str) -> None:
#     capture = FrameCapture()
#     capture.open_stream()

#     fresh = FreshestFrame(capture.capture)

#     entity_found_before = False
#     entity_found = False

#     s3 = S3Service(settings.S3_FILES_BUCKET_NAME)

#     entity_detector = EntityDetector()

#     # get freshest frame, but never the same one twice (cnt increases)
#     count = 0

#     while True:
#         # test that this really takes NO time
#         # (if it does, the camera is actually slower than this loop and we have to wait!)
#         t0 = time.perf_counter()
#         count, frame = fresh.read(seqnumber=count + 1)
#         dt = time.perf_counter() - t0
#         if dt > 0.010:  # 10 milliseconds
#             logger.info(f"NOTICE: read() took {dt:.3f} secs")

#         # logger.info(f"processing {count}...")

#         results = entity_detector.run_inference(frame)
#         if (
#             entity := entity_detector.process_inference_results(
#                 results, CocoClassId.cup
#             )
#         ) is not None:
#             entity_found = True
#             annotated_frame = capture.annotate_frame(
#                 frame, entity.box, entity.name, entity.confidence
#             )
#             latest_frame_with_entity_found = frame
#             latest_annotated_frame_with_entity_found = annotated_frame
#         else:
#             entity_found = False

#         if not entity_found_before and entity_found:
#             now = datetime.now()
#             timestamp = now.strftime("%Y%m%d_%H%M%S")
#             logger.debug(f"Entity entered frame at {now}")

#             frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
#             s3.upload(frame_bytes, f"{uuid.uuid4()}/{entity_to_detect}_entered_{timestamp}.png", mime_type="image/png")

#             annotated_frame_bytes = cv2.imencode(".png", annotated_frame)[1].tobytes()
#             s3.upload(annotated_frame_bytes, f"{uuid.uuid4()}/annotated_{entity_to_detect}_entered_{timestamp}.png", mime_type="image/png")

#             # cv2.imwrite(f"images/{entity_to_detect}_entered_{timestamp}.png", frame)
#             # cv2.imwrite(
#             #     f"images/annotated_{entity_to_detect}_entered_{timestamp}.png",
#             #     annotated_frame,
#             # )
#             entity_found_before = True
#         if entity_found_before and not entity_found:
#             now = datetime.now()
#             timestamp = now.strftime("%Y%m%d_%H%M%S")
#             logger.debug(f"Entity left frame at {now}")

#             frame_bytes = cv2.imencode(".png", latest_frame_with_entity_found)[1].tobytes()
#             s3.upload(frame_bytes, f"{uuid.uuid4()}/{entity_to_detect}_left_{timestamp}.png", mime_type="image/png")

#             annotated_frame_bytes = cv2.imencode(".png", latest_annotated_frame_with_entity_found)[1].tobytes()
#             s3.upload(annotated_frame_bytes, f"{uuid.uuid4()}/annotated_{entity_to_detect}_left_{timestamp}.png", mime_type="image/png")

#             # cv2.imwrite(
#             #     f"images/{entity_to_detect}_left_{timestamp}.png",
#             #     latest_frame_with_entity_found,
#             # )
#             # cv2.imwrite(
#             #     f"images/annotated_{entity_to_detect}_left_{timestamp}.png",
#             #     latest_frame_with_entity_found,
#             # )
#             entity_found_before = False

#     fresh.release()
#     capture.close_stream()


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


# @celery.task(name="detect_object", base=DatabaseTask, bind=True)
@celery.task(name="detect_object", base=DetectionTask, bind=True)
def detect_object(self):
    entity_detector = EntityDetector()

    # output_dir = "images"
    # os.makedirs(output_dir, exist_ok=True)

    try:
        redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    last_id = ">"

    while True:
        try:
            messages = redis_client.xreadgroup(
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
                            redis_client.setex(
                                detection_key, 3600, pickle.dumps(detection_data)
                            )

                            print(
                                f"Detected {entity.name} with confidence {entity.confidence:.2f} at {datetime.fromtimestamp(timestamp)}"
                            )

                            frame_bytes = cv2.imencode(".png", frame)[1].tobytes()
                            frame_s3_key = f"{uuid.uuid4()}/{entity.name}_entered_{timestamp}.png"
                            self.s3_service.upload(frame_bytes, frame_s3_key, mime_type="image/png")

                            annotated_frame_bytes = cv2.imencode(".png", annotated_frame)[1].tobytes()
                            annotated_frame_s3_key = f"{uuid.uuid4()}/annotated_{entity.name}_entered_{timestamp}.png"
                            self.s3_service.upload(annotated_frame_bytes, annotated_frame_s3_key, mime_type="image/png")

                            # Create event using sync session
                            with self.session_maker() as session:
                                event = Event(
                                    entity_id=entity.class_id,
                                    name=entity.name,
                                    timestamp=datetime.fromtimestamp(timestamp),
                                    start_time=datetime.fromtimestamp(timestamp),
                                    s3_key=annotated_frame_s3_key
                                )
                                session.add(event)
                                session.commit()

                    except Exception as e:
                        print(f"Error processing frame: {e}")
                    finally:
                        redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

        except Exception as e:
            print(f"Error reading from stream: {e}")
            time.sleep(1)
