import pickle
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import IO

import numpy as np
import structlog
from celery.utils.log import get_task_logger
from redis import Redis

from schrodinger.celery import celery
from schrodinger.logging import Logger
from schrodinger.worker.redis import RedisTask

log: Logger = structlog.wrap_logger(get_task_logger(__name__))


STREAM_NAME = "frames"


@dataclass
class FrameDimension:
    width: int
    height: int

    def frame_size(self) -> int:
        return self.width * self.height * 3


def get_stream_resolution(rtsp_url: str) -> FrameDimension:
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
        log.fatal(
            "Could not detect resolution",
            returncode=probe_result.returncode,
            stdout=probe_result.stdout,
            stderr=probe_result.stderr,
        )
        raise RuntimeError("Could not detect resolution")

    width, height = map(int, probe_result.stdout.strip().split(","))
    frame_dimension = FrameDimension(width, height)
    log.info("Detected stream resolution", frame_dimensions=frame_dimension)

    return frame_dimension


def publish_single_frame(
    frame_data: IO[str], frame_dim: FrameDimension, redis: Redis
) -> None:
    raw_frame = frame_data.read(frame_dim.frame_size())
    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape(
        (frame_dim.height, frame_dim.width, 3)
    )

    redis.xadd(
        STREAM_NAME,
        {
            "frame": pickle.dumps(frame),
            "timestamp": datetime.now().timestamp(),
        },
        maxlen=1,
    )


def try_killing_process(process: subprocess.Popen | None) -> None:
    if "process" in locals() and process is not None:
        process.kill()


@celery.task(name="fetch_frames", base=RedisTask, bind=True)
def fetch_frames(self, rtsp_url: str):
    process: subprocess.Popen | None = None

    try:
        frame_dim = get_stream_resolution(rtsp_url)
    except RuntimeError:
        frame_dim = FrameDimension(1920, 1080)

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

    while True:
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8,
            )

            log.info("Started FFmpeg capture")

            while True:
                if process.stdout is None:
                    log.info("FFmpeg stream ended")
                    break

                publish_single_frame(process.stdout, frame_dim, self.redis)

            # process.stdout.close()
            # process.stderr.close()
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("FFmpeg process timeout")
            try_killing_process(process)
        except Exception as e:
            log.error("Error in FFmpeg capture", error=e)
            try_killing_process(process)
            time.sleep(2)
