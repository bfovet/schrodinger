from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel
from ultralytics import YOLO


class CocoClassId(IntEnum):
    # https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml
    person = 0
    cat = 15
    bottle = 39
    cup = 41
    couch = 57
    dining_table = 60
    laptop = 63
    remote = 65
    cell_phone = 67
    book = 73


class CocoClassName(StrEnum):
    person = "person"
    cat = "cat"
    bottle = "bottle"
    cup = "cup"
    couch = "couch"
    dining_table = "dining_table"
    laptop = "laptop"
    remote = "remote"
    cell_phone = "cell_phone"
    book = "book"


class DetectedEntity(BaseModel):
    name: CocoClassName
    class_id: CocoClassId
    confidence: float
    box: Any


class EntityDetector:
    def __init__(self):
        self.yolo_model = YOLO("data/yolo11n.pt")

    def run_inference(self, frame):
        # Run YOLOv11 inference
        return self.yolo_model(frame, verbose=False)

    def process_inference_results(
        self, results, entity_id: CocoClassId, confidence_threshold: float = 0.5
    ) -> DetectedEntity | None:
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get class ID and confidence
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    if class_id == entity_id and confidence > confidence_threshold:
                        return DetectedEntity(
                            name=CocoClassName[entity_id.name],
                            class_id=entity_id,
                            confidence=confidence,
                            box=box,
                        )

        return None
