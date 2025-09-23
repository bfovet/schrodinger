import time
from datetime import datetime

import cv2
from celery.utils.log import get_task_logger

from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, EntityDetector
from schrodinger.stream.capture import FrameCapture, FreshestFrame

# SCHRODINGER_RTSP_USERNAME = os.environ.get("USERNAME")
# SCHRODINGER_RTSP_PASSWORD = os.environ.get("PASSWORD")
# SCHRODINGER_RTSP_HOST_IP_ADDRESS = os.environ.get("HOST_IP_ADDRESS")
# SCHRODINGER_RTSP_STREAM_NAME = os.environ.get("STREAM_NAME")

logger = get_task_logger("test")


@celery.task(pydantic=True)
def detect(entity_to_detect: str) -> None:
    capture = FrameCapture()
    capture.open_stream()

    fresh = FreshestFrame(capture.capture)

    entity_found_before = False
    entity_found = False

    entity_detector = EntityDetector()

    # get freshest frame, but never the same one twice (cnt increases)
    count = 0

    while True:
        # test that this really takes NO time
        # (if it does, the camera is actually slower than this loop and we have to wait!)
        t0 = time.perf_counter()
        count, frame = fresh.read(seqnumber=count + 1)
        dt = time.perf_counter() - t0
        if dt > 0.010:  # 10 milliseconds
            logger.info(f"NOTICE: read() took {dt:.3f} secs")

        logger.info(f"processing {count}...")

        results = entity_detector.run_inference(frame)
        if (
            entity := entity_detector.process_inference_results(
                results, CocoClassId.bottle
            )
        ) is not None:
            entity_found = True
            annotated_frame = capture.annotate_frame(
                frame, entity.box, entity.name, entity.confidence
            )
            latest_frame_with_entity_found = annotated_frame
        else:
            entity_found = False

        if not entity_found_before and entity_found:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            logger.debug(f"Entity entered frame at {now}")
            cv2.imwrite(f"images/{entity_to_detect}_entered_{timestamp}.png", frame)
            cv2.imwrite(
                f"images/annotated_{entity_to_detect}_entered_{timestamp}.png",
                annotated_frame,
            )
            entity_found_before = True
        if entity_found_before and not entity_found:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            logger.debug(f"Entity left frame at {now}")
            cv2.imwrite(
                f"images/{entity_to_detect}_left_{timestamp}.png",
                latest_frame_with_entity_found,
            )
            cv2.imwrite(
                f"images/annotated_{entity_to_detect}_left_{timestamp}.png",
                latest_frame_with_entity_found,
            )
            entity_found_before = False

    fresh.release()
    capture.close_stream()
