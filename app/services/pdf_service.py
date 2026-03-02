from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from xml.sax.saxutils import escape

from app.models.booking import Booking, BookingExtra

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
LOGO_PATH = ASSETS_DIR / "logo.png"

# Font preference order: NotoSans (first), then DejaVu, then Helvetica fallback.
FONT_PREFS = [
    ("NotoSans", FONTS_DIR / "NotoSans-Regular.ttf", "NotoSans-Bold", FONTS_DIR / "NotoSans-Bold.ttf"),
    ("DejaVuSans", FONTS_DIR / "DejaVuSans.ttf", "DejaVuSans-Bold", FONTS_DIR / "DejaVuSans-Bold.ttf"),
]


def _try_register(name: str, path: Path) -> bool:
    if not path.exists():
        return False
    try:
        pdfmetrics.registerFont(TTFont(name, str(path)))
        return True
    except Exception:
        return False


def _select_fonts() -> tuple[str, str]:
    normal_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    for normal_name, normal_path, bold_name, bold_path in FONT_PREFS:
        ok_normal = _try_register(normal_name, normal_path)
        ok_bold = _try_register(bold_name, bold_path)
        if ok_normal:
            normal_font = normal_name
            bold_font = bold_name if ok_bold else bold_font
            break

    try:
        pdfmetrics.registerFontFamily(
            normal_font,
            normal=normal_font,
            bold=bold_font,
            italic=normal_font,
            boldItalic=bold_font,
        )
    except Exception:
        pass

    return normal_font, bold_font


def _styles() -> StyleSheet1:
    normal_font, bold_font = _select_fonts()

    styles = StyleSheet1()

    styles.add(
        ParagraphStyle(
            name="Base",
            fontName=normal_font,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#111827"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Heading",
            parent=styles["Base"],
            fontName=bold_font,
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#8B5E34"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Subheading",
            parent=styles["Base"],
            fontSize=10.5,
            textColor=colors.HexColor("#4B5563"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Base"],
            fontName=bold_font,
            fontSize=14.5,
            leading=18,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Label",
            parent=styles["Base"],
            fontName=bold_font,
            textColor=colors.HexColor("#111827"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Value",
            parent=styles["Base"],
            textColor=colors.HexColor("#111827"),
            wordWrap="CJK",  # better wrapping for long strings/URLs
        )
    )

    styles.add(
        ParagraphStyle(
            name="Muted",
            parent=styles["Base"],
            textColor=colors.HexColor("#6B7280"),
            fontSize=9.5,
            leading=12,
        )
    )

    return styles


def _format_dt(dt: datetime) -> str:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Istanbul")
    except Exception:
        tz = None

    if dt.tzinfo and tz:
        local_dt = dt.astimezone(tz)
    elif tz:
        local_dt = dt.replace(tzinfo=tz)
    else:
        local_dt = dt

    return local_dt.strftime("%d.%m.%Y %H:%M")


def _safe_text(value: Optional[str]) -> str:
    # ensure string + escape for ReportLab Paragraph (it parses simple XML-ish markup)
    if not value:
        return ""
    return escape(str(value).strip())


def _money(value: Decimal | str | int | float) -> str:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _kv_table(rows: list[tuple[str, str]], styles: StyleSheet1) -> Table:
    """
    Clean key/value table with subtle row separators and good spacing.
    """
    data = []
    for label, value in rows:
        data.append(
            [
                Paragraph(_safe_text(label), styles["Label"]),
                Paragraph(_safe_text(value), styles["Value"]),
            ]
        )

    table = Table(
        data,
        colWidths=[60 * mm, 110 * mm],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
            ]
        )
    )
    return table


def _section_title(title: str, styles: StyleSheet1) -> Table:
    """
    Section header with a small colored bar on the left.
    """
    bar = Table(
        [[Paragraph("", styles["Base"])]],
        colWidths=[4 * mm],
        rowHeights=[6 * mm],
    )
    bar.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#8B5E34")),
                ("LINEBEFORE", (0, 0), (-1, -1), 0, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    t = Table(
        [[bar, Paragraph(_safe_text(title), styles["Section"])]],
        colWidths=[6 * mm, 166 * mm],
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


def _header(styles: StyleSheet1) -> list:
    story: list = []

    # Logo (optional) + title/subtitle
    logo_cell = ""
    if LOGO_PATH.exists():
        try:
            logo = Image(str(LOGO_PATH))
            logo.drawHeight = 14 * mm
            logo.drawWidth = logo.imageWidth * (logo.drawHeight / float(logo.imageHeight))
            logo_cell = logo
        except Exception:
            logo_cell = ""

    title = Paragraph("GetTransfer", styles["Heading"])
    subtitle = Paragraph("Your ride is booked. Please keep this voucher handy.", styles["Subheading"])

    header_tbl = Table(
        [[logo_cell, Spacer(4 * mm, 0), [title, Spacer(1, 2), subtitle]]],
        colWidths=[20 * mm, 4 * mm, 140 * mm],
    )
    header_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header_tbl)

    # subtle divider
    divider = Table([[""]], colWidths=[166 * mm], rowHeights=[0.7])
    divider.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(divider)
    story.append(Spacer(1, 10))

    return story


def generate_voucher_pdf(booking: Booking, extras: Iterable[BookingExtra], output_path: str | Path) -> Path:
    """
    Generate a voucher PDF with embedded Unicode fonts (Turkish glyphs) and improved layout.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="GetTransfer Voucher",
        author="GetTransfer",
    )

    story: list = []
    story.extend(_header(styles))

    # Voucher details
    story.append(_section_title("Voucher Details", styles))
    story.append(
        _kv_table(
            [
                ("Voucher No", str(booking.voucher_no)),
                ("PNR", str(booking.pnr_code)),
            ],
            styles,
        )
    )

    # Passenger
    story.append(Spacer(1, 8))
    story.append(_section_title("Passenger", styles))
    full_name = f"{(booking.first_name or '').strip()} {(booking.last_name or '').strip()}".strip()
    story.append(
        _kv_table(
            [
                ("Ad Soyad", full_name),
                ("Telefon", str(booking.phone or "")),
                ("E-posta", str(booking.email or "")),
                ("Uçuş Kodu", str(getattr(booking, "flight_code", "") or "")),
            ],
            styles,
        )
    )

    # Transfer
    story.append(Spacer(1, 8))
    story.append(_section_title("Transfer", styles))
    story.append(
        _kv_table(
            [
                ("Tarih & Saat", _format_dt(booking.pickup_datetime)),
                ("Nereden", str(booking.from_text or "")),
                ("Nereye", str(booking.to_text or "")),
                ("Güzergah", str(getattr(booking, "route_url", "") or "")),
            ],
            styles,
        )
    )

    # Vehicle
    story.append(Spacer(1, 8))
    story.append(_section_title("Araç", styles))
    vehicle_line = f"{booking.vehicle_name_snapshot} • {booking.pax} pax • {booking.bags_snapshot} bags"
    story.append(_kv_table([("Tip", vehicle_line)], styles))

    # Payment (make it feel like a small “card”)
    story.append(Spacer(1, 10))
    story.append(_section_title("Ödeme", styles))

    amount_line = f"{_money(Decimal(str(booking.total_price)))} {booking.currency}"
    pay_tbl = _kv_table(
        [
            ("Tutar", amount_line),
            ("Yöntem", "Ödeme nakit olarak sürücüye yapılacaktır."),
        ],
        styles,
    )
    pay_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF9")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(pay_tbl)

    # Extras (optional)
    extras_list = list(extras)
    if extras_list:
        story.append(Spacer(1, 10))
        story.append(_section_title("Ekstralar", styles))
        extra_rows = []
        for extra in extras_list:
            title = f"{extra.title}".strip() if getattr(extra, "title", None) else (extra.code or "")
            code = (extra.code or "").strip()
            left = f"{title} ({code})" if code and title and code not in title else (title or code)
            right = f"{_money(Decimal(str(extra.price)))} {extra.currency}"
            extra_rows.append((left, right))
        story.append(_kv_table(extra_rows, styles))

    # Footer note
    story.append(Spacer(1, 14))
    story.append(Paragraph("Destek: +90 XXX XXX XX XX", styles["Muted"]))

    doc.build(story)
    return output_path
