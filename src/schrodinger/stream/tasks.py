from datetime import datetime
import pickle
import time
import subprocess

import numpy as np

from schrodinger.celery import celery
from schrodinger.worker.redis import RedisTask


STREAM_NAME = "frame_stream"
CONSUMER_GROUP = "detection_group"
CONSUMER_NAME = "detector_1"


def get_stream_resolution(rtsp_url: str) -> tuple[int, int]:
    # fmt: off
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        rtsp_url,
    ]
    # fmt: on

    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)

    if probe_result.returncode != 0:
        raise RuntimeError("Could not detect resolution")

    width, height = map(int, probe_result.stdout.strip().split(","))
    print(f"Detected stream resolution: {width}x{height}")

    return width, height


@celery.task(name="fetch_frames", base=RedisTask, bind=True)
def fetch_frames(self, rtsp_url: str):
    process: subprocess.Popen | None = None
    width, height = get_stream_resolution(rtsp_url)
    while True:
        try:
            frame_size = width * height * 3

            # fmt: off
            ffmpeg_cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-fflags", "nobuffer+discardcorrupt",
                "-flags", "low_delay",
                "-analyzeduration", "1",
                "-probesize", "32",
                "-i", rtsp_url,
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",
                "-an",  # Disable audio
                "-vf", "fps=10",  # Limit to 10 fps to reduce processing load
                "-",
            ]
            # fmt: on

            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8,
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

                self.redis.xadd(
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
            if "process" in locals():
                process.kill()
        except Exception as e:
            print(f"Error in FFmpeg capture: {e}")
            if "process" in locals():
                process.kill()
            time.sleep(2)
