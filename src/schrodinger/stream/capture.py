import threading

import cv2

from schrodinger.config import settings

RTSP_URL = f"rtsp://{settings.SCHRODINGER_RTSP_USERNAME}:{settings.SCHRODINGER_RTSP_PASSWORD}@{settings.SCHRODINGER_RTSP_HOST_IP_ADDRESS}:554/{settings.SCHRODINGER_RTSP_STREAM_NAME}"


class FrameCapture:
    def __init__(self):
        self.capture: cv2.VideoCapture
        # self.status: bool = False

    def open_stream(self):
        self.capture = cv2.VideoCapture(RTSP_URL)

        # Set threading and buffer options to prevent FFmpeg assertion errors
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to prevent lag
        self.capture.set(cv2.CAP_PROP_FPS, 15)  # Limit FPS to reduce load

        # Additional settings for real-time streaming
        self.capture.set(
            cv2.CAP_PROP_FRAME_WIDTH, 640
        )  # Lower resolution for faster processing
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(
            cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G")
        )

        if not self.capture.isOpened():
            raise RuntimeError("Could not open RTSP stream")

    def close_stream(self):
        self.capture.release()

    def read_frame(self):
        captured, frame = self.capture.read()
        if not captured:
            # TODO: log
            print("No frame captured")

        return frame

    def read_num_frames(self):
        for _ in range(3):  # Read and discard a few frames to get real-time
            frame = self.read_frame()

        return frame

    def annotate_frame(self, frame, box, object_name, confidence):
        annotated_frame = frame.copy()

        # Get bounding box coordinates
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # Draw bounding box
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Add label
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


# also acts (partly) like a cv.VideoCapture
# see https://gist.github.com/crackwitz/15c3910f243a42dcd9d4a40fcdb24e40#file-freshest_camera_frame-py-L117
class FreshestFrame(threading.Thread):
    def __init__(self, capture, name="FreshestFrame"):
        self.capture = capture
        assert self.capture.isOpened()

        # this lets the read() method block until there's a new frame
        self.cond = threading.Condition()

        # this allows us to stop the thread gracefully
        self.running = False

        # keeping the newest frame around
        self.frame = None

        # passing a sequence number allows read() to NOT block
        # if the currently available one is exactly the one you ask for
        self.latestnum = 0

        # this is just for demo purposes
        self.callback = None

        super().__init__(name=name)
        self.start()

    def start(self):
        self.running = True
        super().start()

    def release(self, timeout=None):
        self.running = False
        self.join(timeout=timeout)
        self.capture.release()

    def run(self):
        counter = 0
        while self.running:
            # block for fresh frame
            (rv, img) = self.capture.read()
            assert rv
            counter += 1

            # publish the frame
            with self.cond:  # lock the condition for this operation
                self.frame = img if rv else None
                self.latestnum = counter
                self.cond.notify_all()

            if self.callback:
                self.callback(img)

    def read(self, wait=True, seqnumber=None, timeout=None):
        # with no arguments (wait=True), it always blocks for a fresh frame
        # with wait=False it returns the current frame immediately (polling)
        # with a seqnumber, it blocks until that frame is available (or no wait at all)
        # with timeout argument, may return an earlier frame;
        #   may even be (0,None) if nothing received yet

        with self.cond:
            if wait:
                if seqnumber is None:
                    seqnumber = self.latestnum + 1
                if seqnumber < 1:
                    seqnumber = 1

                rv = self.cond.wait_for(
                    lambda: self.latestnum >= seqnumber, timeout=timeout
                )
                if not rv:
                    return (self.latestnum, self.frame)

            return (self.latestnum, self.frame)
