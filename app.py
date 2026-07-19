import colorsys
import ctypes
import math
import os
import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


APP_BG = "#2f2f2f"
PANEL_BG = "#3b3b3b"
TEXT = "#eeeeee"
MUTED = "#b8b8b8"
ACCENT = "#64b5f6"


PALETTE = [
    ("红", (244, 67, 54)),
    ("橙", (255, 152, 0)),
    ("黄", (255, 235, 59)),
    ("绿", (76, 175, 80)),
    ("青", (0, 188, 212)),
    ("蓝", (33, 150, 243)),
    ("紫", (103, 58, 183)),
    ("品红", (233, 30, 99)),
    ("粉", (248, 187, 208)),
    ("棕", (121, 85, 72)),
    ("黑", (0, 0, 0)),
    ("灰", (128, 128, 128)),
    ("白", (255, 255, 255)),
]


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def clamp(value, low, high):
    return max(low, min(high, value))


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def hex_to_rgb(value):
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        raise ValueError("HEX 颜色需要 3 位或 6 位")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hsv_tuple(rgb):
    r, g, b = [channel / 255 for channel in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def rgb_to_hsl_tuple(rgb):
    r, g, b = [channel / 255 for channel in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def rgb_to_cmyk_tuple(rgb):
    r, g, b = [channel / 255 for channel in rgb]
    k = 1 - max(r, g, b)
    if k >= 1:
        return 0, 0, 0, 100
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return c * 100, m * 100, y * 100, k * 100


def srgb_channel_to_linear(channel):
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    r, g, b = [srgb_channel_to_linear(channel) for channel in rgb]
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    x /= 0.95047
    y /= 1.00000
    z /= 1.08883

    def pivot(value):
        if value > 0.008856:
            return value ** (1 / 3)
        return 7.787 * value + 16 / 116

    fx, fy, fz = pivot(x), pivot(y), pivot(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(rgb_a, rgb_b):
    lab_a = rgb_to_lab(rgb_a)
    lab_b = rgb_to_lab(rgb_b)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)))


def similarity_score(rgb_a, rgb_b):
    distance = delta_e(rgb_a, rgb_b)
    return clamp(100 * math.exp(-((distance / 48) ** 2)), 0, 100)


def palette_matches(rgb):
    matches = []
    for name, palette_rgb in PALETTE:
        matches.append((name, palette_rgb, similarity_score(rgb, palette_rgb)))
    return sorted(matches, key=lambda item: item[2], reverse=True)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]


@dataclass
class ScreenSnapshot:
    left: int
    top: int
    width: int
    height: int
    buffer: object

    def get_pixel(self, x, y):
        rel_x = int(x) - self.left
        rel_y = int(y) - self.top
        if rel_x < 0 or rel_y < 0 or rel_x >= self.width or rel_y >= self.height:
            return None
        index = (rel_y * self.width + rel_x) * 4
        blue = self.buffer[index]
        green = self.buffer[index + 1]
        red = self.buffer[index + 2]
        return int(red), int(green), int(blue)


class ScreenCapture:
    SRCCOPY = 0x00CC0020
    BI_RGB = 0
    DIB_RGB_COLORS = 0
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("当前版本使用 Windows 原生屏幕取色 API")
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.configure_winapi()

    def configure_winapi(self):
        self.user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        self.user32.GetSystemMetrics.restype = ctypes.c_int
        self.user32.GetDC.argtypes = [ctypes.c_void_p]
        self.user32.GetDC.restype = ctypes.c_void_p
        self.user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.user32.ReleaseDC.restype = ctypes.c_int

        self.gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
        self.gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
        self.gdi32.CreateCompatibleBitmap.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
        self.gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.gdi32.SelectObject.restype = ctypes.c_void_p
        self.gdi32.BitBlt.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        self.gdi32.BitBlt.restype = ctypes.c_int
        self.gdi32.GetDIBits.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        self.gdi32.GetDIBits.restype = ctypes.c_int
        self.gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
        self.gdi32.DeleteObject.restype = ctypes.c_int
        self.gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
        self.gdi32.DeleteDC.restype = ctypes.c_int

    def snapshot(self):
        left = self.user32.GetSystemMetrics(self.SM_XVIRTUALSCREEN)
        top = self.user32.GetSystemMetrics(self.SM_YVIRTUALSCREEN)
        width = self.user32.GetSystemMetrics(self.SM_CXVIRTUALSCREEN)
        height = self.user32.GetSystemMetrics(self.SM_CYVIRTUALSCREEN)
        if width <= 0 or height <= 0:
            raise RuntimeError("无法读取屏幕尺寸")

        hdc_screen = self.user32.GetDC(None)
        hdc_memory = self.gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = self.gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        old_object = self.gdi32.SelectObject(hdc_memory, hbitmap)

        try:
            if not self.gdi32.BitBlt(
                hdc_memory, 0, 0, width, height, hdc_screen, left, top, self.SRCCOPY
            ):
                raise RuntimeError("屏幕截图失败")

            bitmap_info = BITMAPINFO()
            bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bitmap_info.bmiHeader.biWidth = width
            bitmap_info.bmiHeader.biHeight = -height
            bitmap_info.bmiHeader.biPlanes = 1
            bitmap_info.bmiHeader.biBitCount = 32
            bitmap_info.bmiHeader.biCompression = self.BI_RGB

            buffer = (ctypes.c_ubyte * (width * height * 4))()
            result = self.gdi32.GetDIBits(
                hdc_memory,
                hbitmap,
                0,
                height,
                ctypes.byref(buffer),
                ctypes.byref(bitmap_info),
                self.DIB_RGB_COLORS,
            )
            if result == 0:
                raise RuntimeError("读取屏幕像素失败")
        finally:
            self.gdi32.SelectObject(hdc_memory, old_object)
            self.gdi32.DeleteObject(hbitmap)
            self.gdi32.DeleteDC(hdc_memory)
            self.user32.ReleaseDC(None, hdc_screen)

        return ScreenSnapshot(left, top, width, height, buffer)


class ScreenPickerOverlay(tk.Toplevel):
    def __init__(self, app, snapshot):
        super().__init__(app.root)
        self.app = app
        self.snapshot = snapshot
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#111111", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        geometry = "{}x{}{:+d}{:+d}".format(
            snapshot.width, snapshot.height, snapshot.left, snapshot.top
        )
        self.geometry(geometry)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.18)
        self.lift()
        self.focus_force()

        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Button-1>", self.on_click)
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<KeyPress-Escape>", lambda event: self.destroy())
        self.current_rgb = None

        self.canvas.create_text(
            22,
            18,
            anchor="nw",
            fill="#ffffff",
            text="移动鼠标取样，单击确认，Esc 取消",
            font=("Microsoft YaHei UI", 11),
            tags=("help",),
        )

    def on_motion(self, event):
        rgb = self.snapshot.get_pixel(event.x_root, event.y_root)
        if rgb is None:
            return
        self.current_rgb = rgb
        x = event.x_root - self.snapshot.left
        y = event.y_root - self.snapshot.top
        self.draw_hud(x, y, rgb)

    def on_click(self, _event):
        if self.current_rgb:
            self.app.set_current_rgb(self.current_rgb)
        self.destroy()

    def draw_hud(self, x, y, rgb):
        self.canvas.delete("hud")
        color = rgb_to_hex(rgb)
        self.canvas.create_line(x - 16, y, x + 16, y, fill="#ffffff", tags=("hud",))
        self.canvas.create_line(x, y - 16, x, y + 16, fill="#ffffff", tags=("hud",))

        size = 9
        cell = 8
        box_x = x + 24
        box_y = y + 24
        if box_x + size * cell + 110 > self.snapshot.width:
            box_x = x - size * cell - 132
        if box_y + size * cell + 52 > self.snapshot.height:
            box_y = y - size * cell - 70

        self.canvas.create_rectangle(
            box_x - 8,
            box_y - 8,
            box_x + size * cell + 118,
            box_y + size * cell + 48,
            fill="#202020",
            outline="#ffffff",
            width=1,
            tags=("hud",),
        )
        for gy in range(size):
            for gx in range(size):
                px = self.snapshot.left + x + gx - size // 2
                py = self.snapshot.top + y + gy - size // 2
                sample = self.snapshot.get_pixel(px, py) or rgb
                sample_color = rgb_to_hex(sample)
                self.canvas.create_rectangle(
                    box_x + gx * cell,
                    box_y + gy * cell,
                    box_x + (gx + 1) * cell,
                    box_y + (gy + 1) * cell,
                    fill=sample_color,
                    outline="",
                    tags=("hud",),
                )

        center = size // 2
        self.canvas.create_rectangle(
            box_x + center * cell,
            box_y + center * cell,
            box_x + (center + 1) * cell,
            box_y + (center + 1) * cell,
            outline="#ffffff",
            width=2,
            tags=("hud",),
        )
        info_x = box_x + size * cell + 14
        self.canvas.create_rectangle(
            info_x,
            box_y,
            info_x + 74,
            box_y + 32,
            fill=color,
            outline="#ffffff",
            tags=("hud",),
        )
        self.canvas.create_text(
            info_x,
            box_y + 46,
            anchor="w",
            fill="#ffffff",
            text=color,
            font=("Consolas", 11, "bold"),
            tags=("hud",),
        )


class ColorSenseApp:
    PICKER_SIZE = 220
    HUE_WIDTH = 28
    WHEEL_SIZE = 236
    WHEEL_SEGMENTS = 24

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Color Sense Picker")
        self.set_window_icon()
        self.root.geometry("1080x740")
        self.root.minsize(1040, 700)
        self.root.configure(bg=APP_BG)

        self.capture = ScreenCapture()
        self.current_rgb = (115, 131, 37)
        self.target_rgb = PALETTE[3][1]
        self.hue = rgb_to_hsv_tuple(self.current_rgb)[0] / 360
        self.saturation = rgb_to_hsv_tuple(self.current_rgb)[1] / 100
        self.value = rgb_to_hsv_tuple(self.current_rgb)[2] / 100

        self.square_image = None
        self.hue_image = None
        self.position_image = None
        self.pinned_positions = []
        self.hex_var = tk.StringVar()
        self.target_var = tk.StringVar(value="绿")
        self.status_var = tk.StringVar(value="准备就绪")
        self.position_var = tk.StringVar()
        self.info_vars = {
            "HEX": tk.StringVar(),
            "RGB": tk.StringVar(),
            "HSV": tk.StringVar(),
            "HSL": tk.StringVar(),
            "CMYK": tk.StringVar(),
            "坐标": tk.StringVar(value="-"),
            "目标匹配": tk.StringVar(),
            "最近颜色": tk.StringVar(),
        }

        self.configure_style()
        self.build_ui()
        self.root.bind("<F6>", lambda _event: self.start_screen_pick())
        self.root.bind("<Control-c>", lambda _event: self.copy_hex())
        self.set_current_rgb(self.current_rgb, refresh_picker=True)

    def set_window_icon(self):
        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass

    def configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=APP_BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("TLabel", background=APP_BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL_BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=PANEL_BG, foreground=MUTED)
        style.configure("TButton", padding=(10, 6), background="#4a4a4a", foreground=TEXT)
        style.map("TButton", background=[("active", "#5a5a5a")])
        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT)
        style.configure("TCombobox", fieldbackground="#4a4a4a", background="#4a4a4a", foreground=TEXT)
        style.configure("TEntry", fieldbackground="#222222", foreground=TEXT)

    def build_ui(self):
        header = ttk.Frame(self.root, padding=(14, 12, 14, 8))
        header.pack(fill="x")
        ttk.Label(header, text="颜色程度取色器", font=("Microsoft YaHei UI", 16, "bold")).pack(
            side="left"
        )
        ttk.Button(header, text="屏幕取色 F6", command=self.start_screen_pick).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(header, text="复制 HEX", command=self.copy_hex).pack(side="right", padx=(8, 0))

        body = ttk.Frame(self.root, padding=(14, 6, 14, 10))
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Panel.TFrame", padding=14)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        ttk.Label(
            left,
            text="颜色",
            style="Panel.TLabel",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        picker_row = ttk.Frame(left, style="Panel.TFrame")
        picker_row.pack()
        self.square_canvas = tk.Canvas(
            picker_row,
            width=self.PICKER_SIZE,
            height=self.PICKER_SIZE,
            highlightthickness=0,
            bg=PANEL_BG,
        )
        self.square_canvas.pack(side="left")
        self.hue_canvas = tk.Canvas(
            picker_row,
            width=self.HUE_WIDTH,
            height=self.PICKER_SIZE,
            highlightthickness=0,
            bg=PANEL_BG,
        )
        self.hue_canvas.pack(side="left", padx=(14, 0))
        self.square_canvas.bind("<Button-1>", self.on_square_drag)
        self.square_canvas.bind("<B1-Motion>", self.on_square_drag)
        self.hue_canvas.bind("<Button-1>", self.on_hue_drag)
        self.hue_canvas.bind("<B1-Motion>", self.on_hue_drag)

        swatch_row = ttk.Frame(left, style="Panel.TFrame")
        swatch_row.pack(fill="x", pady=(14, 0))
        self.current_swatch = tk.Canvas(swatch_row, width=54, height=42, highlightthickness=1)
        self.current_swatch.pack(side="left")
        self.target_swatch = tk.Canvas(swatch_row, width=54, height=42, highlightthickness=1)
        self.target_swatch.pack(side="left", padx=(10, 0))
        ttk.Label(swatch_row, text="前景 / 目标", style="Muted.TLabel").pack(
            side="left", padx=(10, 0)
        )

        right = ttk.Frame(body, style="Panel.TFrame", padding=14)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        top_info = ttk.Frame(right, style="Panel.TFrame")
        top_info.grid(row=0, column=0, sticky="ew")
        top_info.columnconfigure(1, weight=1)
        ttk.Label(top_info, text="HEX", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        hex_entry = ttk.Entry(top_info, textvariable=self.hex_var, width=16)
        hex_entry.grid(row=0, column=1, sticky="ew", padx=(10, 8))
        hex_entry.bind("<Return>", lambda _event: self.apply_hex())
        ttk.Button(top_info, text="应用", command=self.apply_hex).grid(row=0, column=2)

        info_grid = ttk.Frame(right, style="Panel.TFrame")
        info_grid.grid(row=1, column=0, sticky="ew", pady=(14, 10))
        info_grid.columnconfigure(1, weight=1)
        labels = ["RGB", "HSV", "HSL", "CMYK", "最近颜色"]
        for row, label in enumerate(labels):
            ttk.Label(info_grid, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w")
            ttk.Label(info_grid, textvariable=self.info_vars[label], style="Panel.TLabel").grid(
                row=row, column=1, sticky="w", padx=(12, 0)
            )

        target = ttk.Frame(right, style="Panel.TFrame")
        target.grid(row=2, column=0, sticky="ew", pady=(6, 12))
        target.columnconfigure(1, weight=1)
        ttk.Label(target, text="判断目标", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.target_combo = ttk.Combobox(
            target,
            textvariable=self.target_var,
            values=[name for name, _rgb in PALETTE],
            state="readonly",
            width=12,
        )
        self.target_combo.grid(row=0, column=1, sticky="w", padx=(12, 8))
        self.target_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_target_changed())
        ttk.Button(target, text="当前色设为目标", command=self.use_current_as_target).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Label(target, textvariable=self.info_vars["目标匹配"], style="Panel.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )

        ttk.Label(right, text="颜色归属程度", style="Panel.TLabel", font=("Microsoft YaHei UI", 12, "bold")).grid(
            row=3, column=0, sticky="w", pady=(8, 8)
        )
        match_area = ttk.Frame(right, style="Panel.TFrame")
        match_area.grid(row=4, column=0, sticky="nsew")
        match_area.columnconfigure(0, weight=1)
        match_area.rowconfigure(0, weight=1)
        self.match_canvas = tk.Canvas(
            match_area,
            height=350,
            bg=PANEL_BG,
            highlightthickness=0,
        )
        self.match_canvas.grid(row=0, column=0, sticky="nsew")

        position_panel = ttk.Frame(match_area, style="Panel.TFrame")
        position_panel.grid(row=0, column=1, sticky="ns", padx=(14, 0))
        ttk.Label(
            position_panel,
            text="色相位置",
            style="Panel.TLabel",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        position_buttons = ttk.Frame(position_panel, style="Panel.TFrame")
        position_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(position_buttons, text="固定位置", command=self.pin_hue_position).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(position_buttons, text="清空", command=self.clear_pinned_positions).pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )
        self.position_canvas = tk.Canvas(
            position_panel,
            width=self.WHEEL_SIZE,
            height=self.WHEEL_SIZE,
            bg=PANEL_BG,
            highlightthickness=0,
        )
        self.position_canvas.pack(pady=(6, 0))
        ttk.Label(
            position_panel,
            textvariable=self.position_var,
            style="Muted.TLabel",
            justify="center",
        ).pack(fill="x", pady=(4, 0))
        right.rowconfigure(4, weight=1)

        status = ttk.Frame(self.root, padding=(14, 6))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var, foreground=MUTED).pack(side="left")

    def refresh_picker_images(self):
        self.square_image = tk.PhotoImage(width=self.PICKER_SIZE, height=self.PICKER_SIZE)
        for y in range(self.PICKER_SIZE):
            value = 1 - y / (self.PICKER_SIZE - 1)
            row = []
            for x in range(self.PICKER_SIZE):
                saturation = x / (self.PICKER_SIZE - 1)
                r, g, b = colorsys.hsv_to_rgb(self.hue, saturation, value)
                row.append("#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255)))
            self.square_image.put("{" + " ".join(row) + "}", to=(0, y))
        self.square_canvas.delete("all")
        self.square_canvas.create_image(0, 0, image=self.square_image, anchor="nw")

        self.hue_image = tk.PhotoImage(width=self.HUE_WIDTH, height=self.PICKER_SIZE)
        for y in range(self.PICKER_SIZE):
            hue = y / (self.PICKER_SIZE - 1)
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
            color = "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
            self.hue_image.put("{" + " ".join([color] * self.HUE_WIDTH) + "}", to=(0, y))
        self.hue_canvas.delete("all")
        self.hue_canvas.create_image(0, 0, image=self.hue_image, anchor="nw")
        self.draw_picker_markers()

    def draw_picker_markers(self):
        self.square_canvas.delete("marker")
        self.hue_canvas.delete("marker")
        x = self.saturation * (self.PICKER_SIZE - 1)
        y = (1 - self.value) * (self.PICKER_SIZE - 1)
        self.square_canvas.create_oval(
            x - 6,
            y - 6,
            x + 6,
            y + 6,
            outline="#ffffff",
            width=2,
            tags=("marker",),
        )
        hue_y = self.hue * (self.PICKER_SIZE - 1)
        self.hue_canvas.create_polygon(
            0,
            hue_y,
            -7,
            hue_y - 6,
            -7,
            hue_y + 6,
            fill="#ffffff",
            outline="#666666",
            tags=("marker",),
        )
        self.hue_canvas.create_polygon(
            self.HUE_WIDTH,
            hue_y,
            self.HUE_WIDTH + 7,
            hue_y - 6,
            self.HUE_WIDTH + 7,
            hue_y + 6,
            fill="#ffffff",
            outline="#666666",
            tags=("marker",),
        )

    def draw_hue_position(self, hue_degrees, saturation, color_name):
        self.position_canvas.delete("all")
        center = self.WHEEL_SIZE / 2
        outer_radius = 92
        inner_radius = 58
        marker_radius = (outer_radius + inner_radius) / 2
        self.draw_24_hue_wheel(center, outer_radius, inner_radius)

        for index, pinned in enumerate(self.pinned_positions, start=1):
            pinned_x, pinned_y = self.hue_point(center, pinned["hue"], outer_radius + 12)
            ring_x1, ring_y1 = self.hue_point(center, pinned["hue"], inner_radius - 2)
            ring_x2, ring_y2 = self.hue_point(center, pinned["hue"], outer_radius + 4)
            pinned_hex = rgb_to_hex(pinned["rgb"])
            self.position_canvas.create_line(
                ring_x1,
                ring_y1,
                ring_x2,
                ring_y2,
                fill=pinned_hex,
                width=3,
            )
            self.position_canvas.create_oval(
                pinned_x - 8,
                pinned_y - 7,
                pinned_x + 8,
                pinned_y + 7,
                fill=pinned_hex,
                outline="#ffffff",
            )
            self.position_canvas.create_text(
                pinned_x,
                pinned_y,
                fill="#ffffff",
                text=str(index),
                font=("Consolas", 8, "bold"),
            )

        marker_x, marker_y = self.hue_point(center, hue_degrees, marker_radius)
        current_hex = rgb_to_hex(self.current_rgb)
        self.position_canvas.create_line(
            center,
            center,
            marker_x,
            marker_y,
            fill="#ffffff",
            dash=(2, 3),
        )
        self.position_canvas.create_oval(
            marker_x - 10,
            marker_y - 10,
            marker_x + 10,
            marker_y + 10,
            fill=current_hex,
            outline="#ffffff",
            width=2,
        )
        self.position_canvas.create_text(
            center,
            center,
            anchor="center",
            fill="#dddddd",
            text="24色\n色相环",
            font=("Microsoft YaHei UI", 9),
            justify="center",
        )
        if saturation < 8:
            label = "低饱和\n色相弱"
        else:
            label = "{}段\n{:.0f}°".format(color_name, hue_degrees)
        relation = self.hue_relation_text(hue_degrees)
        self.position_var.set("{}\n{}\n固定 {} 个".format(label, relation, len(self.pinned_positions)))

    def draw_24_hue_wheel(self, center, outer_radius, inner_radius):
        gap = 1.2
        for index in range(self.WHEEL_SEGMENTS):
            start = index * 360 / self.WHEEL_SEGMENTS + gap
            end = (index + 1) * 360 / self.WHEEL_SEGMENTS - gap
            middle = (start + end) / 2
            r, g, b = colorsys.hsv_to_rgb(middle / 360, 0.92, 0.95)
            color = "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
            points = []
            for step in range(6):
                angle = start + (end - start) * step / 5
                points.extend(self.hue_point(center, angle, outer_radius))
            for step in range(5, -1, -1):
                angle = start + (end - start) * step / 5
                points.extend(self.hue_point(center, angle, inner_radius))
            self.position_canvas.create_polygon(points, fill=color, outline="#141414", width=2)

        self.position_canvas.create_oval(
            center - outer_radius - 12,
            center - outer_radius - 12,
            center + outer_radius + 12,
            center + outer_radius + 12,
            outline="#bbbbbb",
            dash=(4, 3),
        )
        self.position_canvas.create_oval(
            center - inner_radius + 10,
            center - inner_radius + 10,
            center + inner_radius - 10,
            center + inner_radius - 10,
            outline="#dddddd",
        )

    def hue_point(self, center, hue_degrees, radius):
        angle = math.radians(hue_degrees % 360)
        return center + math.cos(angle) * radius, center - math.sin(angle) * radius

    def hue_relation_text(self, hue_degrees):
        if not self.pinned_positions:
            return "未固定对比点"
        nearest = min(
            self.pinned_positions,
            key=lambda pinned: self.hue_distance(hue_degrees, pinned["hue"]),
        )
        distance = self.hue_distance(hue_degrees, nearest["hue"])
        if distance < 15:
            relation = "同类色"
        elif distance < 45:
            relation = "类似色"
        elif distance < 75:
            relation = "邻近色"
        elif distance < 105:
            relation = "中差色"
        elif distance < 150:
            relation = "对比色"
        else:
            relation = "互补色"
        return "最近固定点：{:.0f}° {}".format(distance, relation)

    def hue_distance(self, hue_a, hue_b):
        distance = abs((hue_a % 360) - (hue_b % 360))
        return min(distance, 360 - distance)

    def pin_hue_position(self):
        h, s, _v = rgb_to_hsv_tuple(self.current_rgb)
        top_name = palette_matches(self.current_rgb)[0][0]
        self.pinned_positions.append(
            {
                "hue": h,
                "saturation": s,
                "rgb": self.current_rgb,
                "name": top_name if s >= 8 else "低饱和",
            }
        )
        self.update_output()
        self.status_var.set(
            "已固定第 {} 个色相位置：{} {}".format(
                len(self.pinned_positions), rgb_to_hex(self.current_rgb), self.pinned_positions[-1]["name"]
            )
        )

    def clear_pinned_positions(self):
        count = len(self.pinned_positions)
        self.pinned_positions.clear()
        self.update_output()
        self.status_var.set("已清空 {} 个固定色相位置".format(count))

    def set_current_rgb(self, rgb, refresh_picker=False):
        self.current_rgb = tuple(int(clamp(value, 0, 255)) for value in rgb)
        h, s, v = rgb_to_hsv_tuple(self.current_rgb)
        old_hue = self.hue
        new_hue = h / 360 if s > 0 else self.hue
        hue_delta = abs(new_hue - old_hue)
        hue_changed = min(hue_delta, 1 - hue_delta) > 0.002
        self.hue = new_hue
        self.saturation = s / 100
        self.value = v / 100
        if refresh_picker or hue_changed or self.square_image is None:
            self.refresh_picker_images()
        else:
            self.draw_picker_markers()
        self.update_output()

    def on_square_drag(self, event):
        x = clamp(event.x, 0, self.PICKER_SIZE - 1)
        y = clamp(event.y, 0, self.PICKER_SIZE - 1)
        self.saturation = x / (self.PICKER_SIZE - 1)
        self.value = 1 - y / (self.PICKER_SIZE - 1)
        rgb_float = colorsys.hsv_to_rgb(self.hue, self.saturation, self.value)
        rgb = tuple(int(round(channel * 255)) for channel in rgb_float)
        self.set_current_rgb(rgb)

    def on_hue_drag(self, event):
        y = clamp(event.y, 0, self.PICKER_SIZE - 1)
        self.hue = y / (self.PICKER_SIZE - 1)
        rgb_float = colorsys.hsv_to_rgb(self.hue, self.saturation, self.value)
        rgb = tuple(int(round(channel * 255)) for channel in rgb_float)
        self.current_rgb = rgb
        self.refresh_picker_images()
        self.update_output()

    def update_output(self):
        rgb = self.current_rgb
        hex_value = rgb_to_hex(rgb)
        self.hex_var.set(hex_value)
        self.current_swatch.configure(bg="#1f1f1f")
        self.current_swatch.delete("all")
        self.current_swatch.create_rectangle(4, 4, 50, 38, fill=hex_value, outline="#ffffff")

        self.target_swatch.delete("all")
        self.target_swatch.create_rectangle(
            4, 4, 50, 38, fill=rgb_to_hex(self.target_rgb), outline="#ffffff"
        )

        h, s, v = rgb_to_hsv_tuple(rgb)
        hsl_h, hsl_s, hsl_l = rgb_to_hsl_tuple(rgb)
        c, m, y, k = rgb_to_cmyk_tuple(rgb)
        matches = palette_matches(rgb)
        top_name, _top_rgb, top_score = matches[0]
        target_score = similarity_score(rgb, self.target_rgb)

        self.info_vars["RGB"].set("R {}   G {}   B {}".format(*rgb))
        self.info_vars["HSV"].set("H {:.0f}°   S {:.0f}%   V {:.0f}%".format(h, s, v))
        self.info_vars["HSL"].set("H {:.0f}°   S {:.0f}%   L {:.0f}%".format(hsl_h, hsl_s, hsl_l))
        self.info_vars["CMYK"].set(
            "C {:.0f}%   M {:.0f}%   Y {:.0f}%   K {:.0f}%".format(c, m, y, k)
        )
        self.info_vars["最近颜色"].set("{}，匹配度 {:.1f}%".format(top_name, top_score))
        self.info_vars["目标匹配"].set(
            "当前颜色属于“{}”的程度：{:.1f}%".format(self.target_var.get(), target_score)
        )
        self.draw_match_bars(matches)
        self.draw_hue_position(h, s, top_name)

    def draw_match_bars(self, matches):
        self.match_canvas.delete("all")
        width = max(360, self.match_canvas.winfo_width())
        row_height = 24
        bar_x = 68
        bar_width = width - 158
        for row, (name, rgb, score) in enumerate(matches[:9]):
            y = row * row_height + 8
            color = rgb_to_hex(rgb)
            self.match_canvas.create_text(
                8, y + 9, anchor="w", fill=TEXT, text=name, font=("Microsoft YaHei UI", 10)
            )
            self.match_canvas.create_rectangle(
                38, y + 2, 56, y + 18, fill=color, outline="#777777"
            )
            self.match_canvas.create_rectangle(
                bar_x, y + 4, bar_x + bar_width, y + 16, fill="#252525", outline="#565656"
            )
            self.match_canvas.create_rectangle(
                bar_x,
                y + 4,
                bar_x + bar_width * score / 100,
                y + 16,
                fill=color,
                outline="",
            )
            self.match_canvas.create_text(
                bar_x + bar_width + 12,
                y + 9,
                anchor="w",
                fill=MUTED,
                text="{:.1f}%".format(score),
                font=("Consolas", 10),
            )

    def on_target_changed(self):
        name = self.target_var.get()
        for palette_name, rgb in PALETTE:
            if palette_name == name:
                self.target_rgb = rgb
                break
        self.update_output()

    def use_current_as_target(self):
        self.target_rgb = self.current_rgb
        self.target_var.set("自定义")
        self.update_output()
        self.status_var.set("已把当前颜色设为判断目标")

    def apply_hex(self):
        try:
            rgb = hex_to_rgb(self.hex_var.get())
        except ValueError as exc:
            self.status_var.set(str(exc))
            return
        self.set_current_rgb(rgb, refresh_picker=True)
        self.status_var.set("已应用 HEX {}".format(rgb_to_hex(rgb)))

    def copy_hex(self):
        value = rgb_to_hex(self.current_rgb)
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status_var.set("已复制 {}".format(value))

    def start_screen_pick(self):
        self.status_var.set("正在抓取屏幕...")
        self.root.update_idletasks()
        try:
            snapshot = self.capture.snapshot()
        except Exception as exc:
            self.status_var.set("屏幕取色失败：{}".format(exc))
            return
        self.status_var.set("取色中：移动鼠标，单击确认，Esc 取消")
        ScreenPickerOverlay(self, snapshot)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ColorSenseApp().run()
