# Development

Schrodinger's stack consists of the following elements:

- A backend written in Python, exposing a REST API
- An S3-compatible storage

## Prerequisites

Schrodinger needs a [Python 3](https://www.python.org/downloads/) installation.

## Setup backend

Setting up the backend consists of basically three things:

**1. Start the development containers**

This will start Minio (S3 storage) container. You'll need to have [Docker](https://docs.docker.com/get-started/) installed.

    docker compose up -d

**2. Install Python dependencies**

We use [uv](https://docs.astral.sh/uv/) to manage our Python dependencies. Make sure it's installed on your system.

    uv sync
