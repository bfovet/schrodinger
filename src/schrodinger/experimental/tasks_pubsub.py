from datetime import datetime
import os
import pickle
import time

import cv2
from redis import Redis

from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, EntityDetector


redis_client = Redis("localhost", port=6379, db=0)


STREAM_NAME = "frame_stream"
CONSUMER_GROUP = "detection_group"
CONSUMER_NAME = "detector_1"


@celery.task(name="fetch_frames")
def fetch_frames(rtsp_url: str):
    video = cv2.VideoCapture()
    video.open(rtsp_url)
    # keep the buffer small so we minimize old data
    video.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        if not video.isOpened():
            if not video.open(rtsp_url):
                time.sleep(1)
                continue

        frame_time = datetime.now()
        if video.grab():
            ok, frame = video.retrieve()
            if ok:
                frame_data = {"timestamp": frame_time.timestamp(), "frame": frame}

                redis_client.set("current_frame", pickle.dumps(frame_data), ex=2)
                redis_client.publish("frame_ready", frame_time.timestamp())

    video.release()


@celery.task(name="detect_object")
def detect_object():
    entity_detector = EntityDetector()
    last_processed_timestamp = 0.0

    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)

    pubsub = redis_client.pubsub()
    pubsub.subscribe("frame_ready")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            frame_data_bytes = redis_client.get("current_frame")
            if frame_data_bytes is None:
                continue

            frame_data = pickle.loads(frame_data_bytes)
            timestamp = frame_data["timestamp"]
            frame = frame_data["frame"]

            if timestamp == last_processed_timestamp:
                continue

            last_processed_timestamp = timestamp

            # Run detection
            results = entity_detector.run_inference(frame)
            if (
                entity := entity_detector.process_inference_results(
                    results, CocoClassId.cup
                )
            ) is not None:
                annotated_frame = annotate_frame(
                    frame, entity.box, entity.name, entity.confidence
                )

                cv2.imwrite(f"{output_dir}/{timestamp:.6f}.png", annotated_frame)

                detection_key = f"detection:{timestamp:.6f}"
                detection_data = {
                    "timestamp": timestamp,
                    "object": entity.name,
                    "confidence": entity.confidence,
                    "box": entity.box.xyxy[0].tolist(),
                }
                redis_client.setex(detection_key, 3600, pickle.dumps(detection_data))

                print(f"Detected {entity.name} with confidence {entity.confidence:.2f}")
        except Exception as e:
            print(f"Error processing frame: {e}")


def annotate_frame(frame, box, object_name, confidence):
    annotated_frame = frame.copy()

    # Get bounding box coordinates
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    # Draw bounding box
    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Add label
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
