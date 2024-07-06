
from typing import Tuple
import customtkinter as ctk
import cv2
import numpy
from PIL import Image, ImageTk

class MainWindow(ctk.CTk):

    def __init__(self, fg_color: str | Tuple[str, str] | None = None, **kwargs):
        super().__init__(fg_color, **kwargs)

        self._preview_label = ctk.CTkLabel(self)
        self._preview_label.pack()

    def run(self) -> None:
        self.mainloop()
    
    def set_image(self, imgarr: cv2.typing.MatLike) -> None:
        img = Image.fromarray(cv2.cvtColor(imgarr, cv2.COLOR_BGR2RGB))
        #imgtk = ImageTk.PhotoImage(image=img)
        imgtk = ctk.CTkImage(
            light_image=img,
            size=(640, 360)
        )
        self._preview_label.configure(image=imgtk)
    