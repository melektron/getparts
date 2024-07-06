
from pyzbar import pyzbar
# For this to work with Python3.12 we need to manually patch it to remove the disutils dependency according to this pr:
# https://github.com/NaturalHistoryMuseum/pylibdmtx/pull/90 (because the lib seems to not be well maintained)
from pylibdmtx import pylibdmtx
import enum
import cv2
import dataclasses

class CodeType(enum.Enum):
    DATAMATRIX_2D = 1
    QR_CODE = 2
    BARCODE_128 = 3

@dataclasses.dataclass
class CodeResult:
    data: bytes
    type: CodeType
    _bounds_tl: tuple[int, int]
    _bounds_tr: tuple[int, int]
    _bounds_br: tuple[int, int]
    _bounds_bl: tuple[int, int]

    def draw_bounds(self, image: cv2.typing.MatLike, color: tuple[int, int, int], thickness: int) -> None:
        """
        Draws the bounds of the detected code on the provided opencv buffer.
        """
        cv2.line(
            image,
            self._bounds_tl, self._bounds_tr,
            color, thickness
        )
        cv2.line(
            image,
            self._bounds_tr, self._bounds_br,
            color, thickness
        )
        cv2.line(
            image,
            self._bounds_br, self._bounds_bl,
            color, thickness
        )
        cv2.line(
            image,
            self._bounds_bl, self._bounds_tl,
            color, thickness
        )


def scan_for_codes(frame: cv2.typing.MatLike) -> list[CodeResult]:
    """
    detects various codes on a frame and returns a list of them
    """
    results: CodeResult = []

    # check for a data matrices
    barcodes_2d: list[pylibdmtx.Decoded] = pylibdmtx.decode(
        frame,
        timeout=100,
        max_count=1,
        threshold=50
    )
    if barcodes_2d:
        print(barcodes_2d)
        for code in barcodes_2d:
            rect: pylibdmtx.Rect = code.rect
            results.append(CodeResult(
                code.data,
                CodeType.DATAMATRIX_2D,
                (rect.left, rect.top),
                (rect.left + rect.width, rect.top),
                (rect.left + rect.width, rect.top + rect.height),
                (rect.left, rect.top + rect.height)
            ))
        
    return results