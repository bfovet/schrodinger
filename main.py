from datetime import datetime
import os
import cv2
from dotenv import load_dotenv
import rtsp

load_dotenv()


USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
HOST_IP_ADDRESS = os.environ.get("HOST_IP_ADDRESS")
STREAM_NAME = os.environ.get("STREAM_NAME")


def main():
    rtsp_url = f"rtsp://{USERNAME}:{PASSWORD}@{HOST_IP_ADDRESS}:554/{STREAM_NAME}"

    with rtsp.Client(rtsp_url, verbose=True) as client:
        win_name = "rtsp"
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(win_name,20,20)
        while client.isOpened():
            cv2.imshow(win_name, client.read(raw=True))
            if cv2.waitKey(30) == ord('q'): # wait 30 ms for 'q' input
                break
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)


if __name__ == "__main__":
    main()
