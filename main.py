
import cv2

from src.ui import MainWindow
from src.vsource import VideoSource
from src.scanner import scan_for_codes


FRAME_RATE = 30 
FRAME_TIME = int(1000 / FRAME_RATE)


def main() -> int:
    window = MainWindow()
    camera = VideoSource()

    def update_frame() -> None:
        frame_raw = camera.get_frame()
        frame = frame_raw #cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #frame = cv2.adaptiveThreshold(
        #    frame_raw,
        #    255,
        #    cv2.ADAPTIVE_THRESH_MEAN_C,
        #    cv2.THRESH_BINARY,
        #    31, 10
        #)
        #_, frame = cv2.threshold(
        #    frame_raw,
        #    128,
        #    255,
        #    cv2.THRESH_BINARY
        #)

        found_codes = scan_for_codes(frame)
        for result in found_codes:
            result.draw_bounds(frame, (255, 0, 0), 2)

        window.set_image(frame)
        window.after(FRAME_TIME, update_frame)
    
    window.after(FRAME_TIME, update_frame)
    window.run()

    return 0

if __name__ == "__main__":
    exit(main())