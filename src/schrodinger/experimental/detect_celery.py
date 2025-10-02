"""Detect objects in a realtime stream"""

from datetime import datetime
import os
import multiprocessing as mp
import time

import cv2
import numpy as np

from schrodinger.detection.detection import CocoClassId, EntityDetector

from schrodinger.experimental.tasks import detect_object, fetch_frames
from schrodinger.experimental.tasks import detect_object_streams, fetch_frames_streams


RTSP_URL = os.getenv("RTSP_URL")


def main():
    fetch_frames_task = fetch_frames_streams.delay(RTSP_URL)
    print(f"Started fetch_frames task: {fetch_frames_task.id}")
    detect_object_task = detect_object_streams.delay()
    print(f"Started detect_object task: {detect_object_task.id}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        fetch_frames_task.revoke(terminate=True)
        detect_object_task.revoke(terminate=True)


if __name__ == "__main__":
    main()
