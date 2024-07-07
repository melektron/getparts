
from typing import Tuple, Any
import customtkinter as ctk
import webbrowser
import os
from pathlib import Path
import asyncio
from PIL import Image

from .partinfo import PartInfo


CAMERA_SIZE = (640, 360)
PART_IMAGE_SIZE = (150, 150)    # should be the native size for mouser, and also fits nicely in UI


class InfoField:
    def __init__(
        self, 
        master, 
        label: str, 
        row: int, 
        open: bool = False, 
        clipboard: bool = True, 
        height: int = 0, 
        pady: int = 5
    ) -> None:
        self._master = master
        self._label_value = label
        self._row = row
        self._open = open
        self._clipboard = clipboard
        self._height = height
        self._pady = pady

        self._label = ctk.CTkLabel(
            self._master, 
            text=self._label_value
        )
        self._label.grid(
            row=self._row,
            column=0,
            sticky="W",
            padx=10
        )
        
        if self._height > 0:
            self._value_entry = ctk.CTkTextbox(
                self._master,
                width=500,
                height=self._height,
                state="normal"
            )
        else:
            self._value = ctk.StringVar(self._master, "")
            self._value_entry = ctk.CTkEntry(
                self._master,
                width=(500 - 28 - 10) if self._open else 500,
                textvariable=self._value,
                state="normal"
            )
        self._value_entry.grid(
            row=self._row,
            column=1,
            sticky="W" if self._open else "WE",
            pady=self._pady
        )
        
        if self._clipboard:
            self._clipboard_icon = ctk.CTkImage(
                light_image=Image.open("assets/copy_light.png"),
                dark_image=Image.open("assets/copy_dark.png")
            )
            self._checkmark_icon = ctk.CTkImage(
                light_image=Image.open("assets/check_light.png"),
                dark_image=Image.open("assets/check_dark.png")
            )
            self._clipboard_button = ctk.CTkButton(
                self._master,
                width=28,
                text="",
                image=self._clipboard_icon,
                command=self.copy_to_clipboard
            )
            self._clipboard_button.grid(
                row=self._row,
                column=2,
                sticky="WE",
                padx=10,
                pady=self._pady
            )
        else:
            self._clipboard_button = None

        if self._open:
            self._globe_icon = ctk.CTkImage(
                light_image=Image.open("assets/globe_light.png"),
                dark_image=Image.open("assets/globe_dark.png")
            )
            self._open_button = ctk.CTkButton(
                self._master,
                width=28,
                text="",
                image=self._globe_icon,
                command=self.open_in_browser
            )
            self._open_button.grid(
                row=self._row,
                column=1,
                sticky="E",
                pady=self._pady
            )

    def copy_to_clipboard(self) -> None:
        if isinstance(self._value_entry, ctk.CTkTextbox):
            self._master.clipboard_clear()
            self._master.clipboard_append(self._value_entry.get(1.0, ctk.END))
        else:
            self._master.clipboard_clear()
            self._master.clipboard_append(self._value_entry.get())

        if self._clipboard_button is not None:
            self._clipboard_button.configure(image=self._checkmark_icon)
            self._clipboard_button.after(1000, lambda: self._clipboard_button.configure(image=self._clipboard_icon))
    
    def open_in_browser(self) -> None:
        if isinstance(self._value_entry, ctk.CTkTextbox):
            webbrowser.open(self._value_entry.get(1.0, ctk.END))
        else:
            webbrowser.open(self._value_entry.get())
    
    def set_value(self, val: Any) -> None:
        if isinstance(self._value_entry, ctk.CTkTextbox):
            self._value_entry.delete(1.0, ctk.END)
            self._value_entry.insert(ctk.END, str(val))
        else:
            self._value.set(str(val))


class MainWindow(ctk.CTk):

    def __init__(self, fg_color: str | Tuple[str, str] | None = None, **kwargs):
        super().__init__(fg_color, **kwargs)

        self.resizable(False, False)
        self.title("Mouser GetPart")
        #ctk.set_appearance_mode("light")

        self._camera_label = ctk.CTkLabel(self, text="")
        self._camera_label.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=10,
            pady=10
        )
        self.set_camera_image(Image.new("RGB", CAMERA_SIZE, (0, 0, 0)))
        
        self._part_image_label = ctk.CTkLabel(self, text="")
        self._part_image_label.grid(
            row=1,
            rowspan=5,
            column=1,
            padx=10,
            pady=10,
            sticky="NSE"
        )
        self.set_part_image(Image.new("RGB", PART_IMAGE_SIZE, (0, 0, 0)))

        self._video_source_label = ctk.CTkLabel(
            self, 
            text="Video source:"
        )
        self._video_source_label.grid(
            row=1, column=0, sticky="W", padx=10, pady=5
        )
        self._video_source_strvar = ctk.StringVar(self, "91")
        self._video_source_accepted: str = self._video_source_strvar.get()
        self._video_source_entry = ctk.CTkEntry(
            self,
            width=370,
            textvariable=self._video_source_strvar,
            state="normal",
        )
        self._video_source_entry.bind("<Return>", self._accept_video_source)
        self._video_source_entry.bind("<FocusOut>", self._accept_video_source)
        self._video_source_entry.grid(
            row=1, column=0, sticky="E", padx=10, pady=5,
        )

        self._enable_datamatrix = ctk.BooleanVar(self, True)
        self._enable_datamatrix_check = ctk.CTkCheckBox(
            self, text="Look for 2D datamatrices (Mouser)", 
            onvalue=True, offvalue=False, variable=self._enable_datamatrix
        )
        self._enable_datamatrix_check.grid(
            row=2, column=0, padx=10, pady=5, sticky="W"
        )

        self._enable_barcode_128 = ctk.BooleanVar(self, False)
        self._enable_barcode_128_check = ctk.CTkCheckBox(
            self, text="Look for 1D CODE128 barcodes (no function)",
            onvalue=True, offvalue=False, variable=self._enable_barcode_128
        )
        self._enable_barcode_128_check.grid(
            row=3, column=0, padx=10, pady=5, sticky="W"
        )

        self._enable_qrcode = ctk.BooleanVar(self, False)
        self._enable_qrcode_check = ctk.CTkCheckBox(
            self, text="Look for QR Codes (no function)",
            onvalue=True, offvalue=False, variable=self._enable_qrcode
        )
        self._enable_qrcode_check.grid(
            row=4, column=0, padx=10, pady=5, sticky="W"
        )

        self._image_path_label = ctk.CTkLabel(
            self, 
            text="Save folder: "
        )
        self._image_path_label.grid(
            row=5, column=0, sticky="W", padx=10, pady=5
        )
        self._image_save_path = ctk.StringVar(self, str(Path.home() / "Pictures/components"))
        self._image_path_entry = ctk.CTkEntry(
            self,
            width=370,
            textvariable=self._image_save_path,
            state="normal"
        )
        self._image_path_entry.grid(
            row=5, column=0, sticky="E", padx=10, pady=5,
        )

        self._data_frame = ctk.CTkFrame(self, width=640)
        self._data_frame.grid(
            row=0, rowspan=6,
            column=2,
            padx=10, pady=10,
            sticky="NSEW"
        )

        self.rowconfigure(5, weight=1)
        self.columnconfigure(0, weight=1)

        self._part_info_label = ctk.CTkLabel(
            self._data_frame, 
            text="Part Info", 
            font=("Arial", 32),
            width=640
        )
        self._part_info_label.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="NWE",
            pady=10
        )

        self._field_description = InfoField(self._data_frame, "Description:", row=1)
        self._field_in_stock = InfoField(self._data_frame, "In Stock:", row=2)
        self._field_min_qty = InfoField(self._data_frame, "Minimum Qty:", row=3)
        self._field_qty_multiples = InfoField(self._data_frame, "Qty Multiples:", row=4)
        self._field_manufacturer = InfoField(self._data_frame, "Manufacturer:", row=5)
        self._field_manufacturer_part_number = InfoField(self._data_frame, "MPN:", row=6)
        self._field_supplier_part_number = InfoField(self._data_frame, "SPN:", row=7)
        self._field_currency = InfoField(self._data_frame, "Currency:", row=8)
        self._field_price_breaks = InfoField(self._data_frame, "Price Breaks:", row=9, height=100)
        self._field_packaging_options = InfoField(self._data_frame, "Packaging options:", row=10)
        self._field_details_url = InfoField(self._data_frame, "Supplier URL:", row=11, open=True)

        self._exited = False

        def stop_loop():
            self._exited = True
        self.protocol("WM_DELETE_WINDOW", stop_loop)

    @property
    def exited(self):
        return self._exited

    @property
    def enable_datamatrix(self) -> bool:
        return self._enable_datamatrix.get()
    @property
    def enable_barcode_128(self) -> bool:
        return self._enable_barcode_128.get()
    @property
    def enable_qrcode(self) -> bool:
        return self._enable_qrcode.get()
    
    @property
    def video_source(self) -> str:
        return self._video_source_accepted
    
    def _accept_video_source(self, _) -> None:
        self._video_source_accepted = self._video_source_strvar.get()

    async def run(self) -> None:
        while not self.exited:
            self.update()
            await asyncio.sleep(0.02)
    
    def set_camera_image(self, img: Image.Image) -> None:
        # https://stackoverflow.com/a/44231728
        # rescale image so it fits in camera preview size without distortion
        img.thumbnail(size=CAMERA_SIZE) 
        w, h = img.size
        # paste it in the center of the actual preview area, leaving the rest black
        background = Image.new("RGB", CAMERA_SIZE, "black")
        background.paste(img, ((CAMERA_SIZE[0] - w) // 2, (CAMERA_SIZE[1] - h) // 2))
        # convert to CTkImage to allow DPI rescaling and show on label
        img_ctk = ctk.CTkImage(
            light_image=background,
            size=CAMERA_SIZE
        )
        self._camera_label.configure(image=img_ctk)

    def set_part_image(self, img: Image.Image) -> None:    
        img_ctk = ctk.CTkImage(
            light_image=img,
            size=PART_IMAGE_SIZE
        )
        self._part_image_label.configure(image=img_ctk)
    
    def set_part_info(self, info: PartInfo) -> None:
        self._field_description.set_value(info.description)
        self._field_in_stock.set_value(info.in_stock)
        self._field_min_qty.set_value(info.min_qty)
        self._field_qty_multiples.set_value(info.qty_multiples)
        self._field_manufacturer.set_value(info.manufacturer)
        self._field_manufacturer_part_number.set_value(info.manufacturer_part_number)
        self._field_supplier_part_number.set_value(info.supplier_part_number)
        self._field_currency.set_value(info.currency)
        self._field_price_breaks.set_value("\n".join(f"{item.quantity}:\t{item.price:.03f} {info.currency}" for item in info.price_breaks))
        self._field_packaging_options.set_value(", ".join(info.packaging_options))
        self._field_details_url.set_value(info.details_url)
        if info.image is not None:
            self.set_part_image(info.image)
            save_folder = self._image_save_path.get()
            if save_folder == "":
                return  # user doesn't want to save images
            save_path = os.path.join(save_folder, info.image_url.split("/")[-1])
            print(f"Saving image to: {save_path}")
            info.image.save(save_path)
    