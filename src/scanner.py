
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
    _bounding_points: list[tuple[int, int]] = dataclasses.field(default_factory=list)

    def draw_bounds(self, image: cv2.typing.MatLike, color: tuple[int, int, int], thickness: int) -> None:
        """
        Draws the bounds of the detected code on the provided opencv buffer.
        """
        # don't draw if there is only one point, as that is "pointless"
        if len(self._bounding_points) < 2:
            return
        
        for index, point_b in enumerate(self._bounding_points):
            point_a = self._bounding_points[index - 1]
            cv2.line(
                image,
                point_a, point_b,
                color, thickness
            )


class Scanner:
    def __init__(self) -> None:
        self.check_datamatrix_2d = True
        self.check_barcode_128 = True
        self.check_qr_code = False

    def scan_for_codes(self, frame: cv2.typing.MatLike) -> list[CodeResult]:
        """
        detects various codes on a frame and returns a list of them
        """
        results: CodeResult = []

        if self.check_datamatrix_2d:
            # check for a data matrices
            barcodes_2d: list[pylibdmtx.Decoded] = pylibdmtx.decode(
                frame,
                timeout=100,
                max_count=2,
                threshold=50
            )
            if barcodes_2d:
                #print(barcodes_2d)
                for code in barcodes_2d:
                    # transform coordinates a bit because top is measured from bottom for some reason
                    rect = pylibdmtx.Rect(
                        left=code.rect.left,
                        top=frame.shape[:2][0] - code.rect.top,
                        height=code.rect.height,
                        width=code.rect.width
                    )
                    results.append(CodeResult(
                        code.data,
                        CodeType.DATAMATRIX_2D,
                        [
                            (rect.left, rect.top),
                            (rect.left + rect.width, rect.top),
                            (rect.left + rect.width, rect.top - rect.height),
                            (rect.left, rect.top - rect.height)
                        ]
                    ))
        
        if self.check_barcode_128 or self.check_qr_code:
            barcodes: list[pyzbar.Decoded] = pyzbar.decode(frame)
            if barcodes:
                #print(barcodes)
                for code in barcodes:
                    schema: CodeType = ...
                    if code.type == "CODE128":
                        schema = CodeType.BARCODE_128
                        if not self.check_barcode_128:
                            continue
                    elif code.type == "QRCODE":
                        schema = CodeType.QR_CODE
                        if not self.check_qr_code:
                            continue
                    else:
                        print(f"Unexpected barcode scheme: {code.type}")
                        
                    rect: pylibdmtx.Rect = code.rect
                    results.append(CodeResult(
                        code.data,
                        schema,
                        [(p.x, p.y) for p in code.polygon]
                    ))
            
        return results