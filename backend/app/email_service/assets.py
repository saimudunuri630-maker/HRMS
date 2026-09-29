import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "hrms_logo.png")
LOCK_PATH = os.path.join(ASSETS_DIR, "lock_icon.png")
SHIELD_PATH = os.path.join(ASSETS_DIR, "shield_icon.png")
PROJECT_FOLDER_PATH = os.path.join(ASSETS_DIR, "project_folder_icon.png")
ROLE_PATH = os.path.join(ASSETS_DIR, "role_icon.png")
CALENDAR_PATH = os.path.join(ASSETS_DIR, "calendar_icon.png")
PLAY_PATH = os.path.join(ASSETS_DIR, "play_icon.png")
CALENDAR_CHECK_PATH = os.path.join(ASSETS_DIR, "calendar_check_icon.png")
CHART_PATH = os.path.join(ASSETS_DIR, "chart_icon.png")
DOCUMENT_PATH = os.path.join(ASSETS_DIR, "document_icon.png")
INFO_PATH = os.path.join(ASSETS_DIR, "info_icon.png")

BG_LIGHT_BLUE = (219, 234, 254, 255)  # #dbeafe
BLUE_PRIMARY = (37, 99, 235, 255)     # #2563eb
BLUE_SECONDARY = (59, 130, 246, 255)   # #3b82f6
WHITE = (255, 255, 255, 255)


def _get_pil():
    """Lazy import of Pillow so module loading never fails if assets already exist."""
    try:
        from PIL import Image, ImageDraw
        return Image, ImageDraw
    except ImportError:
        raise ImportError(
            "Pillow is required to dynamically generate email assets. "
            "Please install it using: pip install pillow"
        )


def ensure_asset_files():
    """Ensure all email asset PNG files exist on disk, generating them if needed."""
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if not os.path.exists(LOGO_PATH):
        _generate_logo(LOGO_PATH)

    if not os.path.exists(LOCK_PATH):
        _generate_lock_icon(LOCK_PATH)

    if not os.path.exists(SHIELD_PATH):
        _generate_shield_icon(SHIELD_PATH)

    if not os.path.exists(PROJECT_FOLDER_PATH):
        _generate_project_folder_icon(PROJECT_FOLDER_PATH)

    if not os.path.exists(ROLE_PATH):
        _generate_role_icon(ROLE_PATH)

    if not os.path.exists(CALENDAR_PATH):
        _generate_calendar_icon(CALENDAR_PATH)

    if not os.path.exists(PLAY_PATH):
        _generate_play_icon(PLAY_PATH)

    if not os.path.exists(CALENDAR_CHECK_PATH):
        _generate_calendar_check_icon(CALENDAR_CHECK_PATH)

    if not os.path.exists(CHART_PATH):
        _generate_chart_icon(CHART_PATH)

    if not os.path.exists(DOCUMENT_PATH):
        _generate_document_icon(DOCUMENT_PATH)

    if not os.path.exists(INFO_PATH):
        _generate_info_icon(INFO_PATH)


def _generate_logo(path: str):
    """Generate high-res crisp HRMS logo (2 blue silhouettes)."""
    Image, ImageDraw = _get_pil()
    w, h = 360, 300
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Left person: head & shoulders
    d.ellipse([50, 40, 160, 150], fill=BLUE_PRIMARY)
    d.pieslice([10, 150, 200, 330], start=180, end=360, fill=BLUE_PRIMARY)

    # Right person: head & shoulders
    d.ellipse([200, 40, 310, 150], fill=BLUE_SECONDARY)
    d.pieslice([160, 150, 350, 330], start=180, end=360, fill=BLUE_SECONDARY)

    im_final = im.resize((108, 90), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_lock_icon(path: str):
    """Generate circular light-blue badge with blue padlock icon."""
    Image, ImageDraw = _get_pil()
    w, h = 352, 352
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Circle background
    d.ellipse([10, 10, 342, 342], fill=BG_LIGHT_BLUE)

    # Padlock shackle
    d.arc([116, 75, 236, 195], start=180, end=0, fill=BLUE_PRIMARY, width=28)
    d.line([116, 135, 116, 185], fill=BLUE_PRIMARY, width=28)
    d.line([236, 135, 236, 185], fill=BLUE_PRIMARY, width=28)

    # Padlock body
    d.rounded_rectangle([92, 172, 260, 272], radius=24, fill=BLUE_PRIMARY)

    # Keyhole
    d.ellipse([164, 204, 188, 228], fill=WHITE)
    d.polygon([(170, 222), (182, 222), (186, 248), (166, 248)], fill=WHITE)

    im_final = im.resize((176, 176), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_shield_icon(path: str):
    """Generate circular light-blue badge with blue shield check icon."""
    Image, ImageDraw = _get_pil()
    w, h = 320, 320
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # Circle background
    d.ellipse([10, 10, 310, 310], fill=BG_LIGHT_BLUE)

    # Shield polygon
    points = [
        (160, 68),
        (238, 98),
        (238, 174),
        (160, 254),
        (82, 174),
        (82, 98),
    ]
    d.polygon(points, fill=BG_LIGHT_BLUE, outline=BLUE_PRIMARY, width=22)

    # Checkmark inside shield
    d.line([(126, 160), (148, 184)], fill=BLUE_PRIMARY, width=20)
    d.line([(148, 184), (196, 136)], fill=BLUE_PRIMARY, width=20)

    im_final = im.resize((160, 160), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_project_folder_icon(path: str):
    """Generate circular light-blue badge with blue project folder icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    # folder back tab
    d.rounded_rectangle([60, 80, 115, 105], radius=6, fill=BLUE_PRIMARY)
    # folder body
    d.rounded_rectangle([60, 95, 180, 165], radius=10, fill=BLUE_PRIMARY)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_role_icon(path: str):
    """Generate circular light-blue badge with blue role / person icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.ellipse([95, 60, 145, 110], fill=BLUE_PRIMARY)
    d.pieslice([65, 115, 175, 215], start=180, end=360, fill=BLUE_PRIMARY)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_calendar_icon(path: str):
    """Generate circular light-blue badge with blue calendar icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.rounded_rectangle([65, 75, 175, 175], radius=10, outline=BLUE_PRIMARY, width=12)
    d.line([(65, 105), (175, 105)], fill=BLUE_PRIMARY, width=10)
    d.rounded_rectangle([85, 62, 97, 85], radius=4, fill=BLUE_PRIMARY)
    d.rounded_rectangle([143, 62, 155, 85], radius=4, fill=BLUE_PRIMARY)
    for x in (90, 120, 150):
        for y in (125, 150):
            d.ellipse([x-5, y-5, x+5, y+5], fill=BLUE_PRIMARY)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_play_icon(path: str):
    """Generate circular light-blue badge with blue right-pointing play triangle."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.polygon([(96, 75), (164, 120), (96, 165)], fill=BLUE_PRIMARY)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_calendar_check_icon(path: str):
    """Generate circular light-blue badge with blue calendar check icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.rounded_rectangle([65, 75, 175, 175], radius=10, outline=BLUE_PRIMARY, width=12)
    d.line([(65, 105), (175, 105)], fill=BLUE_PRIMARY, width=10)
    d.rounded_rectangle([85, 62, 97, 85], radius=4, fill=BLUE_PRIMARY)
    d.rounded_rectangle([143, 62, 155, 85], radius=4, fill=BLUE_PRIMARY)
    d.line([(96, 142), (114, 160)], fill=BLUE_PRIMARY, width=12)
    d.line([(114, 160), (150, 122)], fill=BLUE_PRIMARY, width=12)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_chart_icon(path: str):
    """Generate circular light-blue badge with blue 3-bar chart icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.rounded_rectangle([75, 125, 99, 170], radius=6, fill=BLUE_PRIMARY)
    d.rounded_rectangle([108, 90, 132, 170], radius=6, fill=BLUE_PRIMARY)
    d.rounded_rectangle([141, 110, 165, 170], radius=6, fill=BLUE_PRIMARY)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_document_icon(path: str):
    """Generate circular light-blue badge with blue document icon."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BG_LIGHT_BLUE)
    d.rounded_rectangle([75, 65, 165, 175], radius=10, outline=BLUE_PRIMARY, width=12)
    d.line([(100, 105), (140, 105)], fill=BLUE_PRIMARY, width=10)
    d.line([(100, 128), (140, 128)], fill=BLUE_PRIMARY, width=10)
    d.line([(100, 150), (125, 150)], fill=BLUE_PRIMARY, width=10)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def _generate_info_icon(path: str):
    """Generate solid blue circular badge with white info letter 'i'."""
    Image, ImageDraw = _get_pil()
    w, h = 240, 240
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    d.ellipse([10, 10, 230, 230], fill=BLUE_PRIMARY)
    d.ellipse([107, 55, 133, 81], fill=WHITE)
    d.rounded_rectangle([107, 102, 133, 185], radius=6, fill=WHITE)

    im_final = im.resize((120, 120), Image.Resampling.LANCZOS)
    im_final.save(path, "PNG")


def get_email_assets() -> dict[str, bytes]:
    """Load and return raw bytes for OTP email inline CID assets."""
    ensure_asset_files()

    def _read(p: str) -> bytes:
        with open(p, "rb") as f:
            return f.read()

    return {
        "hrms-logo": _read(LOGO_PATH),
        "lock-icon": _read(LOCK_PATH),
        "shield-icon": _read(SHIELD_PATH),
    }


def get_project_assignment_email_assets() -> dict[str, bytes]:
    """Load and return raw bytes for all inline CID project assignment email assets."""
    ensure_asset_files()

    def _read(p: str) -> bytes:
        with open(p, "rb") as f:
            return f.read()

    return {
        "hrms-logo": _read(LOGO_PATH),
        "project-icon": _read(PROJECT_FOLDER_PATH),
        "role-icon": _read(ROLE_PATH),
        "calendar-icon": _read(CALENDAR_PATH),
        "play-icon": _read(PLAY_PATH),
        "calendar-check-icon": _read(CALENDAR_CHECK_PATH),
        "chart-icon": _read(CHART_PATH),
        "document-icon": _read(DOCUMENT_PATH),
        "info-icon": _read(INFO_PATH),
    }
