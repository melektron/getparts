
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

        scanner.check_datamatrix_2d = window.enable_datamatrix
        scanner.check_barcode_128 = window.enable_barcode_128
        scanner.check_qr_code = window.enable_qrcode
        found_codes = scanner.scan_for_codes(frame)
        for result in found_codes:
            result.draw_bounds(frame, (0, 255, 0), 2)
            # only fetch if we got a different datamatrix than the last one we already fetched
            if result.type == CodeType.DATAMATRIX_2D and last_code != result.data:
                last_code = result.data
                info = await request_part_info_mouser(result.data)
                if info is not None:
                    window.set_part_info(info)
                    if info.image is not None:
                        window.set_part_image(info.image)

        window.set_camera_image(frame)
        await asyncio.sleep(0.02)

async def main() -> int:

    await asyncio.gather(
        window.run(),
        image_pipeline()
    ) 

    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))