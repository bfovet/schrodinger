"""Detect objects in a realtime stream"""

import ctypes
from datetime import datetime
import os
import multiprocessing as mp
import time

import cv2
import numpy as np

from schrodinger.detection.detection import CocoClassId, EntityDetector

# from schrodinger.experimental.tasks import detect_object, fetch_frames


RTSP_URL = os.getenv("RTSP_URL")


def fetch_frames(
    rtsp_url: str, shared_arr, shared_frame_time, frame_ready, frame_shape
):
    arr = np.frombuffer(shared_arr.get_obj(), dtype=np.uint8).reshape(frame_shape)

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
                shared_frame_time.value = frame_time.timestamp()
                arr[:] = frame

                with frame_ready:
                    frame_ready.notify_all()

    video.release()


def detect_object(shared_arr, shared_frame_time, frame_ready, frame_shape):
    arr = np.frombuffer(shared_arr.get_obj(), dtype=np.uint8).reshape(frame_shape)

    now = datetime.now().timestamp()

    frame_time = 0.0

    entity_detector = EntityDetector()

    while True:
        with frame_ready:
            if (
                shared_frame_time.value == frame_time
                or (now - shared_frame_time.value) > 0.5
            ):
                frame_ready.wait()

        frame_time = shared_frame_time.value
        frame = arr.copy()

        results = entity_detector.run_inference(frame)
        if (
            entity := entity_detector.process_inference_results(
                results, CocoClassId.cup
            )
        ) is not None:
            annotated_frame = annotate_frame(
                frame, entity.box, entity.name, entity.confidence
            )

            cv2.imwrite(f"{frame_time:6f}.png", annotated_frame)


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


def main():
    # fetch_frames_task = fetch_frames.delay(RTSP_URL)
    # detect_object_task = detect_object.delay()

    video = cv2.VideoCapture(RTSP_URL)
    ok, frame = video.read()
    if ok:
        frame_shape = frame.shape
    else:
        print("Unable to capture video stream")
        exit(1)

    video.release()

    flat_array_length = frame_shape[0] * frame_shape[1] * frame_shape[2]
    shared_arr = mp.Array(ctypes.c_uint8, flat_array_length)
    shared_frame_time = mp.Value("d", 0.0)
    frame_ready = mp.Condition()

    capture_process = mp.Process(
        target=fetch_frames,
        args=(RTSP_URL, shared_arr, shared_frame_time, frame_ready, frame_shape),
    )
    capture_process.daemon = True

    detection_process = mp.Process(
        target=detect_object,
        args=(shared_arr, shared_frame_time, frame_ready, frame_shape),
    )
    detection_process.daemon = True

    capture_process.start()
    print(f"capture_process pid={capture_process.pid}")
    detection_process.start()
    print(f"detection_process pid={detection_process.pid}")

    capture_process.join()
    detection_process.join()


if __name__ == "__main__":
    main()
