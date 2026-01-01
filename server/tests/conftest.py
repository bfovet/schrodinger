from pathlib import Path

import cv2
import pytest

tests_dir = Path(__file__).parent


@pytest.fixture
def frame_without_cup():
    return cv2.imread(
        (tests_dir / "images" / "DC62798B5318_20251106_175601083.jpeg").as_posix()
    )


@pytest.fixture
def frame_with_cup():
    return cv2.imread(
        (tests_dir / "images" / "DC62798B5318_20251106175614188.jpeg").as_posix()
    )


@pytest.fixture
def frame_with_cup_annotated():
    return cv2.imread(
        (
            tests_dir / "images" / "DC62798B5318_20251106175614188_annotated.jpeg"
        ).as_posix()
    )
