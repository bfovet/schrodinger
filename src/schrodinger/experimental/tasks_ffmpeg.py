# from datetime import datetime
# import os
# import pickle
# import time

# import cv2
# import redis

# from schrodinger.celery import celery
# from schrodinger.detection.detection import CocoClassId, EntityDetector


# @celery.task(name="detect_object")
# def detect_object_streams():
#     entity_detector = EntityDetector()

#     output_dir = "images"
#     os.makedirs(output_dir, exist_ok=True)

#     try:
#         redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
#     except redis.exceptions.ResponseError as e:
#         if "BUSYGROUP" not in str(e):
#             raise

#     last_id = ">"

#     while True:
#         try:
#             messages = redis_client.xreadgroup(
#                 CONSUMER_GROUP,
#                 CONSUMER_NAME,
#                 {STREAM_NAME: last_id},
#                 count=1,
#                 block=100
#             )

#             if not messages:
#                 continue

#             for _, stream_messages in messages:
#                 for message_id, message_data in stream_messages:
#                     try:
#                         frame_data = pickle.loads(message_data[b"frame_data"])
#                         timestamp = frame_data["timestamp"]
#                         frame = frame_data["frame"]

#                         results = entity_detector.run_inference(frame)
#                         if (
#                             entity := entity_detector.process_inference_results(
#                                 results, CocoClassId.cup
#                             )
#                         ) is not None:
#                             annotated_frame = annotate_frame(
#                                 frame, entity.box, entity.name, entity.confidence
#                             )

#                             cv2.imwrite(f"{output_dir}/{timestamp:.6f}.png", annotated_frame)

#                             detection_key = f"detection:{timestamp:.6f}"
#                             detection_data = {
#                                 "timestamp": timestamp,
#                                 "object": entity.name,
#                                 "confidence": entity.confidence,
#                                 "box": entity.box.xyxy[0].tolist(),
#                             }
#                             redis_client.setex(detection_key, 3600, pickle.dumps(detection_data))

#                             print(f"Detected {entity.name} with confidence {entity.confidence:.2f} at {datetime.fromtimestamp(timestamp)}")
#                     except Exception as e:
#                         print(f"Error processing frame: {e}")
#                     finally:
#                         redis_client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

#         except Exception as e:
#             print(f"Error reading from stream: {e}")
#             time.sleep(1)


# def annotate_frame(frame, box, object_name, confidence):
#     annotated_frame = frame.copy()
#     x1, y1, x2, y2 = map(int, box.xyxy[0])

#     cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

#     label = f"{object_name}: {confidence:.2f}"
#     label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
#     cv2.rectangle(
#         annotated_frame,
#         (x1, y1 - label_size[1] - 10),
#         (x1 + label_size[0], y1),
#         (0, 255, 0),
#         -1,
#     )
#     cv2.putText(
#         annotated_frame,
#         label,
#         (x1, y1 - 5),
#         cv2.FONT_HERSHEY_SIMPLEX,
#         0.6,
#         (0, 0, 0),
#         2,
#     )

#     return annotated_frame
