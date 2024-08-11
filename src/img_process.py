"""
ELEKTRON (c) 2024 - now
Written by melektron
www.elektron.work
06.07.24 11:51

Image processing worker process
"""

from multiprocessing.connection import Connection
import asyncio
import typing
import dataclasses
import cv2

from .video_source import VideoSource
from .scanner import Scanner, CodeType, CodeResult

@dataclasses.dataclass
class WorkerCommand:
    exit: bool
    video_source: str
    enable_datamatrix: bool
    enable_barcode_128: bool
    enable_qrcode: bool


@dataclasses.dataclass
class WorkerResponse:
    frame: cv2.typing.MatLike
    found_codes: list[CodeResult]


async def async_pipe_recv(reader: Connection) -> typing.Any:
    """
    Asynchronously ready from a multiprocessing.Pipe Connection object,
    asynchronously pausing the task until data is available to read.

    Inspiration: https://stackoverflow.com/a/62098165
    
    :returns: The received data
    """
    data_available = asyncio.Event()
    asyncio.get_event_loop().add_reader(reader.fileno(), data_available.set)

    while not reader.poll():
        await data_available.wait()
        data_available.clear()

    return reader.recv()


def image_process(pipe: Connection) -> None:
    camera = VideoSource()
    scanner = Scanner()

    while True:
        # Receive command from main process
        cmd = pipe.recv()
        if not isinstance(cmd, WorkerCommand):
            print("Invalid worker command, worker process exiting")
            break
            
        # exit process if commanded
        if cmd.exit:
            break
        
        # read and process frame
        frame_raw = camera.get_frame(cmd.video_source)
        frame = cv2.cvtColor(frame_raw, cv2.COLOR_BGR2RGB)

        scanner.check_datamatrix_2d = cmd.enable_datamatrix
        scanner.check_barcode_128 = cmd.enable_barcode_128
        scanner.check_qr_code =  cmd.enable_qrcode
        found_codes = scanner.scan_for_codes(frame)

        # send the response back to main process
        pipe.send(WorkerResponse(
            frame,
            found_codes
        ))
    
    # before exiting, close pipe
    if not pipe.closed:
        pipe.close()
