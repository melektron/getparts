
from multiprocessing.connection import Connection
import asyncio
import typing
import dataclasses
from PIL import Image
import cv2

from .video_source import VideoSource
from .scanner import Scanner, CodeType
from .partinfo import request_part_info_mouser, PartInfo

@dataclasses.dataclass
class WorkerCommand:
    exit: bool
    video_source: str
    enable_datamatrix: bool
    enable_barcode_128: bool
    enable_qrcode: bool


@dataclasses.dataclass
class WorkerResponse:
    frame: Image.Image
    part_info: PartInfo | None = None   # optional, only if part info was found


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

    last_code: bytes = ""

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

        info: PartInfo | None = None
        for result in found_codes:
            # only fetch if we got a different datamatrix than the last one we already fetched
            # and only look up the first detected code
            # if we found datamatrix and we haven't found any valid part in this frame yet:
            if result.type == CodeType.DATAMATRIX_2D and info is not ...:
                # draw bounds in green to signify the detected code
                result.draw_bounds(frame, (0, 255, 0), 2)
                # if we already looked this up previously, no need to repeat
                if last_code == result.data:
                    continue
                # otherwise save and request info
                last_code = result.data
                info = request_part_info_mouser(result.data)

            else:
                # other detected codes are marked red
                result.draw_bounds(frame, (255, 0, 0), 2)

        # send the response back to main process
        pipe.send(WorkerResponse(
            Image.fromarray(frame),
            info
        ))
    
    # before exiting, close pipe
    if not pipe.closed:
        pipe.close()
