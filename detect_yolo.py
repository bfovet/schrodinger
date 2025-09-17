from datetime import datetime
from enum import IntEnum
import os
import time
import cv2
from dotenv import load_dotenv
import rtsp
from ultralytics import YOLO

load_dotenv()

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
HOST_IP_ADDRESS = os.environ.get("HOST_IP_ADDRESS")
STREAM_NAME = os.environ.get("STREAM_NAME")

# Load YOLOv11 model
model = YOLO("data/yolo11n.pt")  # You can use yolo11s.pt, yolo11m.pt, yolo11l.pt, yolo11x.pt for better accuracy


# https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml
class CocoClassId(IntEnum):
    person = 0
    cat = 15
    bottle = 39
    couch = 57
    dining_table = 60
    laptop = 63
    remote = 65
    cell_phone = 67
    book = 73


def detect_cat_and_save_frame(frame, frame_count):
    """
    Detect cats in the frame and save it with bounding boxes if cats are found
    """
    # Run YOLOv11 inference
    results = model(frame, verbose=False)

    cat_detected = False
    person_detected = False
    annotated_frame = frame.copy()
    
    # Process results
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                # Get class ID and confidence
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                if class_id == CocoClassId.cat and confidence > 0.5:
                    cat_detected = True

                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add label
                    label = f"Cat: {confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), (0, 255, 0), -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                if class_id == CocoClassId.person and confidence > 0.5:
                    person_detected = True

                    # Get bounding box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

                    # Add label
                    label = f"Person: {confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), (0, 0, 255), -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    if cat_detected and person_detected:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cat_and_person_detected_{timestamp}_{frame_count:04d}.png"
        cv2.imwrite(filename, annotated_frame)
        print(f"Cat and person detected! Saved frame: {filename}")
        return True

    if cat_detected:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cat_detected_{timestamp}_{frame_count:04d}.png"
        cv2.imwrite(filename, annotated_frame)
        print(f"Cat detected! Saved frame: {filename}")

    if person_detected:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"person_detected_{timestamp}_{frame_count:04d}.png"
        cv2.imwrite(filename, annotated_frame)
        print(f"Person detected! Saved frame: {filename}")

    if cat_detected or person_detected:
        return True

    return False


def main():
    rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{HOST_IP_ADDRESS}:554/{STREAM_NAME}"
    
    # Alternative: Use OpenCV VideoCapture with threading options
    # This often resolves FFmpeg threading issues
    cap = cv2.VideoCapture(rtsp_url)
    
    # Set threading and buffer options to prevent FFmpeg assertion errors
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to prevent lag
    cap.set(cv2.CAP_PROP_FPS, 15)  # Limit FPS to reduce load
    
    # Additional settings for real-time streaming
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Lower resolution for faster processing
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
    
    if not cap.isOpened():
        print("Error: Could not open RTSP stream")
        return
    
    try:
        win_name = "RTSP Cat Detection"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(win_name, 20, 20)

        frame_count = 0
        consecutive_failures = 0
        max_failures = 10

        print("Starting cat detection...")
        print("Press 'q' to quit")

        while True:
            # Flush buffer by reading multiple frames to get the latest
            for _ in range(3):  # Read and discard a few frames to get real-time
                ret, frame = cap.read()
                if not ret:
                    break
            
            if ret:
                consecutive_failures = 0  # Reset failure counter
                frame_count += 1
                
                # Add timestamp overlay to verify real-time capture
                # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                # cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                #           0.7, (0, 255, 255), 2)

                # Detect cats and save frame if found
                cat_found = detect_cat_and_save_frame(frame, frame_count)
                
                # Optional: Display the frame (comment out if running headless)
                cv2.imshow(win_name, frame)
                
                # Check for "q" key press to quit
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

                # Minimal delay - let the detection processing be the bottleneck
                # time.sleep(0.1)  # Commented out for real-time
                
            else:
                consecutive_failures += 1
                print(f"Error reading frame (attempt {consecutive_failures}/{max_failures})")
                
                # If too many failures, try to reconnect
                if consecutive_failures >= max_failures:
                    print("Too many failures, attempting to reconnect...")
                    cap.release()
                    time.sleep(2)  # Wait before reconnecting
                    cap = cv2.VideoCapture(rtsp_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, 15)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
                    consecutive_failures = 0
                
                time.sleep(1)  # Wait before retrying
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()