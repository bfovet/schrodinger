from datetime import datetime
import os
import pickle
import time
import subprocess
import numpy as np

import cv2
import redis
from redis import Redis

from schrodinger.config import settings
from schrodinger.celery import celery
from schrodinger.detection.detection import CocoClassId, EntityDetector


redis_client = Redis(settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


STREAM_NAME = "frame_stream"
CONSUMER_GROUP = "detection_group"
CONSUMER_NAME = "detector_1"


def get_stream_resolution(rtsp_url: str) -> tuple[int, int]:
    probe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0',
        rtsp_url
    ]

    probe_result = subprocess.run(
        probe_cmd,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if probe_result.returncode != 0:
        raise RuntimeError("Could not detect resolution")

    width, height = map(int, probe_result.stdout.strip().split(','))
    print(f"Detected stream resolution: {width}x{height}")

    return width, height


@celery.task(name="fetch_frames")
def fetch_frames_streams(rtsp_url: str):
    width, height = get_stream_resolution(rtsp_url)
    while True:
        try:
            frame_size = width * height * 3
            
            # FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-fflags', 'nobuffer+discardcorrupt',
                '-flags', 'low_delay',
                '-analyzeduration', '1',
                '-probesize', '32',
                '-i', rtsp_url,
                '-f', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-an',            # Disable audio
                '-vf', 'fps=10',  # Limit to 10 fps to reduce processing load
                '-'
            ]
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            print(f"Started FFmpeg capture from {rtsp_url}")
            
            while True:
                raw_frame = process.stdout.read(frame_size)
                
                if len(raw_frame) != frame_size:
                    print("FFmpeg stream ended")
                    break
                
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((height, width, 3))
                
                frame_time = datetime.now()
                frame_data = {"timestamp": frame_time.timestamp(), "frame": frame}
                
                redis_client.xadd(
                    STREAM_NAME,
                    {
                        "frame_data": pickle.dumps(frame_data),
                        "timestamp": frame_time.timestamp(),
                    },
                    maxlen=1,
                )
            
            process.stdout.close()
            process.stderr.close()
            process.terminate()
            process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            print("FFmpeg process timeout")
            if 'process' in locals():
                process.kill()
        except Exception as e:
            print(f"Error in FFmpeg capture: {e}")
            if 'process' in locals():
                try:
                    process.kill()
                except:
                    pass
            time.sleep(2)


@celery.task(name="detect_object")
def detect_object_streams():
    entity_detector = EntityDetector()

    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)

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
                block=100
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

                            cv2.imwrite(f"{output_dir}/{timestamp:.6f}.png", annotated_frame)

                            detection_key = f"detection:{timestamp:.6f}"
                            detection_data = {
                                "timestamp": timestamp,
                                "object": entity.name,
                                "confidence": entity.confidence,
                                "box": entity.box.xyxy[0].tolist(),
                            }
                            redis_client.setex(detection_key, 3600, pickle.dumps(detection_data))

                            print(f"Detected {entity.name} with confidence {entity.confidence:.2f} at {datetime.fromtimestamp(timestamp)}")
                    except Exception as e:
                        print(f"Error processing frame: {e}")
                    finally:
                        redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

        except Exception as e:
            print(f"Error reading from stream: {e}")
            time.sleep(1)


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
