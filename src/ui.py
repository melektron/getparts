"""
ELEKTRON (c) 2024 - now
Written by melektron
www.elektron.work
06.07.24 11:51

GetParts GUI
"""

from typing import Tuple, Any
import customtkinter as ctk
import tkinter as tk
import tktooltip
import webbrowser
import os
import cv2
import numpy
from pathlib import Path
import asyncio
from PIL import Image

from .partinfo import PartInfo
from .scanner import CodeResult, CodeType
from src.partinfo import request_part_info_mouser, PartInfo


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
        self.title("Mouser GetParts")
        #ctk.set_appearance_mode("light")

        self._camera_label = ctk.CTkLabel(self, text="")
        self._camera_label.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=10,
            pady=10
        )
        # tooltip for the frame which will be modified
        self._code_tooltip = tktooltip.ToolTip(self._camera_label, "", refresh=0.2)
        self._code_tooltip.hide()

        # prepare complex functionality of camera label
        self._current_input_image: cv2.typing.MatLike = ...
        self._current_codes: list[CodeResult] = []
        self._current_hovered_code: CodeResult | None = None
        self._currently_selected_code: CodeResult | None = None
        self._currently_displayed_code: CodeResult | None = None
        self._current_mouse_x_ui: int = 0
        self._current_mouse_y_ui: int = 0
        self._current_mouse_x_image: int = 0
        self._current_mouse_y_image: int = 0
        self._ui_to_image_offsets: tuple[int, int] = (0, 0)
        self._ui_to_image_coordinate_factor: float = 1.0
        self._mouse_in_frame: bool = False
        # register events to track mouse
        self._camera_label.bind("<Enter>", self._on_mouse_enter_frame)
        self._camera_label.bind("<Leave>", self._on_mouse_leave_frame)
        self._camera_label.bind("<Motion>", self._on_mouse_move_in_frame)
        self._camera_label.bind("<Button-1>", self._on_mouse_click_frame)
        self.set_scanning_results(numpy.array(Image.new("RGB", CAMERA_SIZE, (0, 0, 0))), [])
        self._request_task: asyncio.Task | None = None
        
        self._part_image_label = ctk.CTkLabel(self, text="")
        self._part_image_label.grid(
            row=1,
            rowspan=5,
            column=1,
            padx=10,
            pady=10,
            sticky="NSE"
        )
        self._set_part_image(Image.new("RGB", PART_IMAGE_SIZE, (0, 0, 0)))

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
            text="No Results", 
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

    def _on_mouse_enter_frame(self, *_) -> None:
        self._mouse_in_frame = True
    def _on_mouse_leave_frame(self, *_) -> None:
        self._mouse_in_frame = False
    def _on_mouse_move_in_frame(self, e: tk.Event):
        self._current_mouse_x_ui = e.x
        self._current_mouse_y_ui = e.y
        # convert to image coords and save
        self._current_mouse_x_image = int((e.x - self._ui_to_image_offsets[0]) * self._ui_to_image_coordinate_factor)
        self._current_mouse_y_image = int((e.y - self._ui_to_image_offsets[1]) * self._ui_to_image_coordinate_factor)
        self._update_camera_view()
    
    def _on_mouse_click_frame(self, *_):
        if self._current_hovered_code is not None:
            self._currently_selected_code = self._current_hovered_code
            self._request_analyse_code(self._currently_selected_code)
        else:
            self._currently_selected_code = None
    
    def _to_ui_coords(self, point: tuple[int, int]) -> tuple[int, int]:
        """ Converts input image coordinates from scanner to UI coordinates """
        return (
            int(point[0] / self._ui_to_image_coordinate_factor + self._ui_to_image_offsets[0]),
            int(point[1] / self._ui_to_image_coordinate_factor + self._ui_to_image_offsets[1])
        )

    async def run(self) -> None:
        while not self.exited:
            self.update()
            await asyncio.sleep(0.02)
    
    def set_scanning_results(self, img: cv2.typing.MatLike, codes: list[CodeResult]) -> None:
        self._current_input_image = img
        self._current_codes = codes
        self._update_camera_view()

        # if no code is manually selected, try to find automatically
        if self._currently_selected_code is None:
            for code in codes:
                # request analysis of all datamatrixes
                if code.type == CodeType.DATAMATRIX_2D:
                    self._request_analyse_code(code)
                # TODO: automatically option inventree codes
                # others are ignored for now
                else:
                    pass
    
    def _get_hovered_code(self) -> CodeResult | None:
        # assuming codes never overlap, get the first one that is hovered.
        for code in self._current_codes:
            if code.check_in_bounds((self._current_mouse_x_image, self._current_mouse_y_image)):
                return code
    
    def _update_camera_view(self) -> None:
        # https://stackoverflow.com/a/44231728
        # rescale image so it fits in camera preview size without distortion
        img = Image.fromarray(self._current_input_image)
        real_w, real_h = img.size   # save original size
        img.thumbnail(size=CAMERA_SIZE) 
        ui_w, ui_h = img.size
        # calculate scaling factor and save it, so mouse handler can convert UI coordinates to image
        # coordinates. Before the first frame after size changes (e.g. startup) the conversion might
        # be wrong but for all following ones the correct factor is saved.
        self._ui_to_image_coordinate_factor = real_w / ui_w
        # also calculate how much the picture is shifted if aspect ratio is different
        self._ui_to_image_offsets = ((CAMERA_SIZE[0] - ui_w) // 2, (CAMERA_SIZE[1] - ui_h) // 2)
        
        # paste it in the center of the actual preview area, leaving the rest black
        background = Image.new("RGB", CAMERA_SIZE, "black")
        background.paste(img, self._ui_to_image_offsets)

        # get that as opencv image to allow drawing
        canvas: cv2.typing.MatLike = numpy.array(background)

        # prepare detection mode drawing (happens last)
        mode_text = "Manual" if self._currently_selected_code is not None else "Auto"
        mode_color = (10, 60, 255) if self._currently_selected_code is not None else (0, 255, 0)

        # draw codes
        self._current_hovered_code = None   # reset
        for code in self._current_codes:
            if (
                code.check_in_bounds((self._current_mouse_x_image, self._current_mouse_y_image))
                and self._mouse_in_frame
            ):
                code.draw_bounds(canvas, (255, 255, 0), 1, self._to_ui_coords)
                self._current_hovered_code = code   # save code

            elif self._currently_displayed_code is not None and self._currently_displayed_code.data == code.data:
                code.draw_bounds(canvas, mode_color, 1, self._to_ui_coords)

            else: 
                code.draw_bounds(canvas, (255, 0, 0), 1, self._to_ui_coords)
        
        # if any code is hovered, set the cursor differently
        if self._current_hovered_code is not None:
            self._camera_label.configure(cursor="hand2")
            self._code_tooltip.msg = self._current_hovered_code.data.decode()
            self._code_tooltip.show()
        else:
            self._camera_label.configure(cursor="arrow")
            self._code_tooltip.hide()

        # draw detection mode last to not be overlapped by any code borders
        cv2.putText(canvas, f"Detection: {mode_text}", (10, 20), cv2.QT_FONT_NORMAL, 0.5, mode_color, 1, cv2.LINE_AA)

        # convert to CTkImage to allow DPI rescaling and show on label
        img_ctk = ctk.CTkImage(
            light_image=Image.fromarray(canvas),
            size=CAMERA_SIZE
        )
        self._camera_label.configure(image=img_ctk)
    
    def _request_analyse_code(self, code: CodeResult) -> None:
        # don't start multiple requests
        if self._request_task is not None:
            return
        
        # don't re-analyze previous codes
        if self._currently_displayed_code is not None and self._currently_displayed_code.data == code.data:
            return
        self._currently_displayed_code = code

        # change text to indicate request started
        self._part_info_label.configure(text="Searching...")

        # start request in background
        async def bg_request():
            info = await request_part_info_mouser(code.data)
            self._set_part_info(info)
        self._request_task = asyncio.Task(bg_request())

        # clean up after done
        def complete(*_):
            self._request_task = None
        self._request_task.add_done_callback(complete)


    def _set_part_info(self, info: PartInfo | None) -> None:
        if info is None:
            self._part_info_label.configure(text="No Results")
            self._field_description.set_value("")
            self._field_in_stock.set_value("")
            self._field_min_qty.set_value("")
            self._field_qty_multiples.set_value("")
            self._field_manufacturer.set_value("")
            self._field_manufacturer_part_number.set_value("")
            self._field_supplier_part_number.set_value("")
            self._field_currency.set_value("")
            self._field_price_breaks.set_value("")
            self._field_packaging_options.set_value("")
            self._field_details_url.set_value("")
            self._set_part_image(Image.new("RGB", PART_IMAGE_SIZE, (0, 0, 0)))
            return
        
        self._part_info_label.configure(text="Part Info")
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
            self._set_part_image(info.image)
            save_folder = self._image_save_path.get()
            if save_folder == "":
                return  # user doesn't want to save images
            save_path = os.path.join(save_folder, info.image_url.split("/")[-1])
            print(f"Saving image to: {save_path}")
            info.image.save(save_path)
        else:
            self._set_part_image(Image.new("RGB", PART_IMAGE_SIZE, (0, 0, 0)))
    
    def _set_part_image(self, img: Image.Image) -> None:
        img.thumbnail(size=PART_IMAGE_SIZE) 
        ui_w, ui_h = img.size
        
        # paste it in the center of the actual view area, leaving the rest black
        background = Image.new("RGB", PART_IMAGE_SIZE, "black")
        background.paste(img, ((PART_IMAGE_SIZE[0] - ui_w) // 2, (PART_IMAGE_SIZE[1] - ui_h) // 2))

        img_ctk = ctk.CTkImage(
            light_image=background,
            size=PART_IMAGE_SIZE
        )
        self._part_image_label.configure(image=img_ctk)