
import cv2
import asyncio
from concurrent.futures import ProcessPoolExecutor

from src.ui import MainWindow
from src.video_source import VideoSource
from src.scanner import Scanner, CodeType
from src.partinfo import request_part_info_mouser


FRAME_RATE = 30 
FRAME_TIME = int(1000 / FRAME_RATE)


window = MainWindow()
camera = VideoSource()
scanner = Scanner()

async def image_pipeline() -> None:
    last_code: bytes = ""

    while not window.exited:
        frame_raw = camera.get_frame()
        frame = cv2.cvtColor(frame_raw, cv2.COLOR_BGR2RGB)

        found_codes = scanner.scan_for_codes(frame)
        for result in found_codes:
            result.draw_bounds(frame, (0, 255, 0), 2)
            if result.type == CodeType.DATAMATRIX_2D and last_code != result.data:
                print("new code")
                print(await request_part_info_mouser(result.data))
                last_code = result.data


        window.set_image(frame)
        await asyncio.sleep(0.02)

async def main() -> int:

    await asyncio.gather(
        window.run(),
        image_pipeline()
    ) 

    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))