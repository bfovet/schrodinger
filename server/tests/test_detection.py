from schrodinger.detection.detection import EntityDetector, CocoClassId
from schrodinger.detection.tasks import annotate_frame


def test_detect_nothing(frame_without_cup):
    detector = EntityDetector()
    results = detector.run_inference(frame_without_cup)
    entity = detector.process_inference_results(results, CocoClassId.cup)
    assert entity is None


def test_detect_cup(frame_with_cup):
    detector = EntityDetector()
    results = detector.run_inference(frame_with_cup)
    entity = detector.process_inference_results(results, CocoClassId.cup)
    assert entity is not None
    assert entity.name == "cup"
    assert entity.class_id == CocoClassId.cup
    assert entity.confidence > 0.89


def test_annotate_cup(frame_with_cup, frame_with_cup_annotated):
    detector = EntityDetector()
    results = detector.run_inference(frame_with_cup)
    entity = detector.process_inference_results(results, CocoClassId.cup)
    assert entity is not None
    assert (
        annotate_frame(frame_with_cup, entity.box, entity.name, entity.confidence).all()
        == frame_with_cup_annotated.all()
    )
