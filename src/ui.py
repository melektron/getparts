
from typing import Tuple
import customtkinter as ctk
import cv2
import asyncio
from PIL import Image

class MainWindow(ctk.CTk):

    def __init__(self, fg_color: str | Tuple[str, str] | None = None, **kwargs):
        super().__init__(fg_color, **kwargs)

        self._preview_label = ctk.CTkLabel(self)
        self._preview_label.grid(
            row=0,
            column=0
        )

        self._enable_datamatrix_check = ctk.CTkCheckBox(
            self, text="Look for 2D datamatrices (Mouser)"
        )
        self._enable_datamatrix_check.grid(
            row=1, column=0, padx=10, pady=10, sticky="W"
        )

        self._enable_barcode_128_check = ctk.CTkCheckBox(
            self, text="Look for 1D CODE128 barcodes (no function)"
        )
        self._enable_barcode_128_check.grid(
            row=2, column=0, padx=10, sticky="W"
        )

        self._enable_qrcode_check = ctk.CTkCheckBox(
            self, text="Look for QR Codes (no function)"
        )
        self._enable_qrcode_check.grid(
            row=3, column=0, padx=10, pady=10, sticky="W"
        )

        self._data_frame = ctk.CTkFrame(self, width=640)
        self._data_frame.grid(
            row=0, rowspan=2,
            column=1,
            padx=10, pady=10
        )


        self._exited = False

        def stop_loop():
            self._exited = True
        self.protocol("WM_DELETE_WINDOW", stop_loop)

    @property
    def exited(self):
        return self._exited

    async def run(self) -> None:
        while not self.exited:
            self.update()
            await asyncio.sleep(0.02)
    
    def set_image(self, imgarr: cv2.typing.MatLike) -> None:
        
        if self.exited:
            return
        
        img = Image.fromarray(imgarr)
        img_ctk = ctk.CTkImage(
            light_image=img,
            size=(640, 360)
        )
        self._preview_label.configure(image=img_ctk)
    