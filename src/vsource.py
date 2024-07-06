import cv2
import numpy

class VideoSource:
    def __init__(self) -> None:
        print("Starting video stream...")
        #self._cap = cv2.VideoCapture("http://192.168.1.69/live")#91)
        self._cap = cv2.VideoCapture(91)
        if self._cap is None or not self._cap.isOpened():
            raise RuntimeError('Error starting video stream\n\n')
        #self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    def get_frame(self) -> cv2.typing.MatLike:
        _, frame = self._cap.read()
        return frame


