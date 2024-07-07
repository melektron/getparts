import cv2
import numpy

class VideoSource:
    def __init__(self) -> None:
        self._current_video_source: str = ""
        self._cap: cv2.VideoCapture | None = None
    
    def _open_source(self) -> bool:
        """
        Opens a capture. This assumes that any previous captures
        have already been released and cleaned up, as it simply
        overwrites self._cap.

        :returns: True when opened successfully
        :returns: False if source is not ready for read
        """
        if self._current_video_source == "":
            return False    # no source specified, don't even try to open
        
        # differentiate between video devices and paths
        source_specific: int | str = ...
        if self._current_video_source.isnumeric():
            source_specific = int(self._current_video_source)
        else:
            source_specific = self._current_video_source
        
        self._cap = cv2.VideoCapture(source_specific)
        if self._cap is None:
            print(f"Couldn't open video source '{self._current_video_source}': None")
            return False
        elif not self._cap.isOpened():
            print(f"Couldn't open video source '{self._current_video_source}': not open")
            self._cap = None
            return False
        else:
            print(f"Successfully opened video source '{self._current_video_source}'")
            return True

    def _select_source(self, src: str) -> bool:
        """
        Attempts to switch to a video source if currently a different
        one or no source at all is open, does nothing otherwise.

        :returns: True when source is selected and ready for read
        :returns: False if source is not ready for read
        """
        # if correct source is selected
        if self._current_video_source == src:
            # if it's open and working
            if self._cap is not None and self._cap.isOpened():
                return True # do nothing
            # close if existing at all
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            # attempt to open the source
            return self._open_source()
        
        # if the source is different from the current one
        else:
            # close capture if not already closed
            if self._cap is not None and self._cap.isOpened():
                print("Closing previous capture...")
                self._cap.release()
                self._cap = None
            elif self._cap is not None:
                print("Forgetting previous capture...")
                self._cap = None
            # open new capture
            self._current_video_source = src
            return self._open_source()

        ##self._cap = cv2.VideoCapture("http://192.168.1.69/live")#91)
        #self._cap = cv2.VideoCapture(91)
        #if self._cap is None or not self._cap.isOpened():
        #    raise RuntimeError('Error starting video stream\n\n')
        ##self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)

    def get_frame(self, src: str) -> cv2.typing.MatLike:
        frame: cv2.typing.MatLike = ...
        if self._select_source(src):
            _, frame = self._cap.read()
        else:
            # create blank frame
            frame = numpy.zeros(shape=[360, 640, 3], dtype=numpy.uint8) # shape: height, width, color components
            # draw error text on it
            cv2.putText(
                frame,
                f"Cannot open video source:",
                (20,30),
                cv2.FONT_HERSHEY_SIMPLEX,
                .5,
                (0, 0, 255), # BGR
                1,
                cv2.LINE_AA
            )
            cv2.putText(
                frame,
                f"'{src}'",
                (20,50),
                cv2.FONT_HERSHEY_SIMPLEX,
                .5,
                (0, 0, 255), # BGR
                1,
                cv2.LINE_AA
            )

        return frame


