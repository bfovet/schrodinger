# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Schrodinger is a real-time cat detection system that captures RTSP streams from a home camera, processes frames using YOLO object detection, and saves frames when a cat (or other entities) is detected. The system uses Celery for asynchronous task processing and stores detected frames in S3-compatible storage.

## Development Setup

### Install dependencies
```bash
uv sync
```

### Start development services
Starts PostgreSQL, Redis, and MinIO (S3 storage):
```bash
docker compose up -d
```

### Run the API server locally
```bash
uv run fastapi dev src/schrodinger/app.py
```

### Run Celery worker
```bash
uv run celery -A schrodinger.celery.celery worker --loglevel=info
```

### Code formatting and linting
```bash
uv run ruff check .
uv run ruff format .
uv run isort .
```

## Architecture

### Core Components

**FastAPI Application** (`src/schrodinger/app.py`)
- Exposes REST API at `/api/v1`
- Health endpoint at `/health`
- On startup, launches two Celery tasks: `fetch_frames_streams` and `detect_object_streams`
- Manages async and sync database connections with optional read replica support

**Detection Pipeline** (FFmpeg-based, current implementation)
1. `fetch_frames_streams` task (`src/schrodinger/experimental/tasks_ffmpeg.py:52`) - Captures frames from RTSP stream using FFmpeg subprocess, publishes to Redis stream
2. `detect_object_streams` task (`src/schrodinger/experimental/tasks_ffmpeg.py:124`) - Consumes frames from Redis stream, runs YOLO inference, saves annotated frames when entity detected

**Entity Detection** (`src/schrodinger/detection/detection.py`)
- Uses YOLO11n model from Ultralytics (`data/yolo11n.pt`)
- `EntityDetector` class runs inference and processes results
- `CocoClassId` enum defines detectable objects (cat=15, cup=41, etc.)
- Returns `DetectedEntity` with name, class_id, confidence, and bounding box

**Stream Processing**
- Redis Streams for producer-consumer pattern between frame capture and detection
- Stream name: `frame_stream`, consumer group: `detection_group`
- Frames serialized with pickle and stored with maxlen=1 (only latest frame)

### Configuration

**Settings** (`src/schrodinger/config.py`)
- Environment-based config using Pydantic Settings
- Loads from `.env` (development) or `.env.testing` (testing)
- All settings prefixed with `SCHRODINGER_`
- Key settings:
  - RTSP connection: `RTSP_USERNAME`, `RTSP_PASSWORD`, `RTSP_HOST_IP_ADDRESS`, `RTSP_STREAM_NAME`
  - PostgreSQL: `POSTGRES_*` for write, `POSTGRES_READ_*` for optional read replica
  - Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
  - S3: `S3_ENDPOINT_URL` (set to `http://127.0.0.1:9000` for local MinIO)

**Environment files**
- `.env` - Local development configuration (not committed)
- `.env.template` - Template showing required variables

### Database

**PostgreSQL with SQLAlchemy**
- Async engine (`asyncpg`) for API operations
- Sync engine (`psycopg2`) for specific operations
- Optional read replica support (check `settings.is_read_replica_configured()`)
- `AsyncSessionMiddleware` provides session per request

**Models** (`src/schrodinger/models/`)
- `EntityDetectedEvent` - Tracks detection events with start/end times and S3 URLs

**Kit Framework** (`src/schrodinger/kit/`)
- Reusable database utilities in `kit/db/postgres.py`
- Repository base class in `kit/repository/base.py`
- SQLAlchemy extensions in `kit/extensions/sqlalchemy/`

### Storage

**S3 Integration** (`src/schrodinger/integrations/aws/s3/`)
- `S3Service` - Upload/download files
- `S3Client` - Low-level boto3 wrapper
- Supports both AWS S3 and MinIO (local development)
- Buckets: `SCHRODINGER_S3_FILES_BUCKET_NAME` (private), `SCHRODINGER_S3_FILES_PUBLIC_BUCKET_NAME` (public)

### Celery Tasks

**Task Configuration** (`src/schrodinger/celery.py`)
- Broker and backend: Redis
- Includes tasks from `schrodinger.detection.tasks` and `schrodinger.experimental.tasks_ffmpeg`

**Detection Tasks**
- Current: FFmpeg-based pipeline in `experimental/tasks_ffmpeg.py`
- Legacy: OpenCV-based in `detection/tasks.py` (single-threaded with `FreshestFrame` helper)

## Key Implementation Details

### RTSP Stream Processing
- FFmpeg subprocess reads RTSP stream with low-latency flags (`nobuffer`, `discardcorrupt`, `low_delay`)
- Downsampled to 10 fps to reduce processing load
- Frames converted to numpy arrays (BGR24 format, shape: height x width x 3)

### Object Detection
- YOLO model path: `data/yolo11n.pt` (must exist in project root)
- Default confidence threshold: 0.5
- Detects COCO dataset classes (80 classes total, see `CocoClassId`)
- Currently configured to detect "cup" in production tasks (can be changed to `CocoClassId.cat` for cat detection)

### Frame Annotation
- Bounding boxes drawn in green (0, 255, 0)
- Labels show: "{object_name}: {confidence:.2f}"
- Annotated frames saved to `images/` directory or uploaded to S3

## Docker Deployment

Services defined in `docker-compose.yml`:
- `schrodinger` - FastAPI app (port 8000)
- `celery-worker` - Background task processor
- `db` - PostgreSQL 18.0
- `redis` - Redis 8.2.1
- `minio` - S3-compatible storage (ports 9000, 9001)
- `minio-setup` - One-time bucket configuration

The app container uses `Dockerfile` which includes FFmpeg installation.

## Common Patterns

### Accessing Database Session
In API endpoints, session is available via middleware or dependency injection. Check existing endpoints in `detection/endpoints.py` for examples.

### Adding New Detectable Objects
1. Add to `CocoClassId` and `CocoClassName` enums
2. Update task to detect new class (change `CocoClassId.cup` to desired class)
3. Refer to COCO dataset for class IDs: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml

## Git Commit Guidelines

All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`

**Examples:**
- `feat(detection): add support for dog detection`
- `fix(stream): resolve FFmpeg buffer overflow issue`
- `docs: update RTSP configuration guide`
- `refactor(celery): simplify task error handling`
