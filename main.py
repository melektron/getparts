"""
ELEKTRON (c) 2024 - now
Written by melektron
www.elektron.work
06.07.24 11:51

UI Application for scanning Mouser Labels and downloading part info from the mouser API
inspired by maholli/getparts.
"""

import asyncio
import multiprocessing as mp
from PIL import Image

from src.ui import MainWindow
from src.img_process import async_pipe_recv, image_process, WorkerCommand, WorkerResponse

FRAME_RATE = 30 
FRAME_TIME = int(1000 / FRAME_RATE)


async def image_pipeline(window: MainWindow) -> None:
    # start image worker
    main_pipe, worker_pipe = mp.Pipe(duplex=True)
    process = mp.Process(target=image_process, args=(worker_pipe,))
    process.start()

    while not window.exited:
        main_pipe.send(WorkerCommand(
            exit=False, 
            video_source=window.video_source, 
            enable_datamatrix=window.enable_datamatrix,
            enable_barcode_128=window.enable_barcode_128,
            enable_qrcode=window.enable_qrcode
        ))

        resp = await async_pipe_recv(main_pipe)
        if not isinstance(resp, WorkerResponse):
            print("Invalid worker response, commanding process exit")
            break
            
        window.set_scanning_results(resp.frame, resp.found_codes)

        await asyncio.sleep(0.02)
    
    # tell process to stop
    main_pipe.send(WorkerCommand(
        exit=True, 
        video_source="", 
        enable_datamatrix=False,
        enable_barcode_128=False,
        enable_qrcode=False
    ))
    process.join()


async def main() -> int:
    window = MainWindow()

    await asyncio.gather(
        window.run(),
        image_pipeline(window)
    )
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))