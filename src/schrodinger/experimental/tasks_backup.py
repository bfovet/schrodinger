from datetime import datetime
import pickle
import time

import cv2
import redis
from redis import Redis

from schrodinger.celery import celery


redis_client = Redis("localhost", port=6379, db=0)


@celery.task()
def detect_object():
    try:
        redis_client.xgroup_create("frames", "detect_object", id="0", mkstream=True)
    except redis.exceptions.ResponseError:
        pass

    while True:
        frames = redis_client.xreadgroup(
            "detect_object",
            "consumer1",
            {"frames": ">"},
            count=1,
            block=2000,  # Block for 2 seconds
        )

        for stream_name, stream_frame in frames:
            for frame_id, frame_data in stream_frame:
                timestamp = frame_data[b"timestamp"].decode()
                data = pickle.loads(frame_data[b"frame"])
                print(f"Received frame at timestamp {timestamp}")

                # Acknowledge message
                redis_client.xack("frames", "detect_object", frame_id)

                cv2.imwrite(f"{timestamp}.png", data)


@celery.task()
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
                # _, buffer = cv2.imencode(".png", frame)
                # frame_bytes = buffer.tobytes()
                frame_bytes = pickle.dumps(frame)
                redis_client.xadd(
                    "frames",
                    {"timestamp": frame_time.timestamp(), "frame": frame_bytes},
                    maxlen=1000,
                )
                # redis.set(f"frame:{frame_time.timestamp()}", frame_bytes)

    video.release()
