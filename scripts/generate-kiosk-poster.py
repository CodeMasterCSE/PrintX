#!/usr/bin/env python3
"""
PrintX — Kiosk Signage Poster Generator
Generates a printable, high-resolution A4 signage poster (PDF) for physical placement
at HP Smart Tank 585 self-service campus kiosks.
"""

import sys
import io
import argparse
import socket
from pathlib import Path
import fitz  # PyMuPDF
import qrcode
from PIL import Image


def get_local_lan_ip() -> str:
    """Discovers the active local Wi-Fi or LAN IPv4 address for phone access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_kiosk_poster(
    kiosk_code: str = "KIOSK-01",
    kiosk_name: str = "Central Library Terminal 01",
    base_url: str = "http://localhost:5173",
    output_path: str = "kiosk_poster_KIOSK-01.pdf"
) -> str:
    # Auto-resolve local LAN IP so phones on the same Wi-Fi can scan and open
    if "localhost" in base_url or "127.0.0.1" in base_url:
        lan_ip = get_local_lan_ip()
        if lan_ip != "127.0.0.1":
            base_url = f"http://{lan_ip}:5173"

    portal_url = f"{base_url}/print?device={kiosk_code}"
    print(f"[*] Generating QR code for portal URL: {portal_url}")

    # 1. Generate High-Res QR Code Image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(portal_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGB")
    qr_bytes_io = io.BytesIO()
    qr_img.save(qr_bytes_io, format="PNG")
    qr_bytes = qr_bytes_io.getvalue()

    # 2. Create A4 Document (595.28 x 841.89 points)
    doc = fitz.open()
    page = doc.new_page(width=595.28, height=841.89)

    # Background Top Banner (Slate 900)
    header_rect = fitz.Rect(0, 0, 595.28, 140)
    page.draw_rect(header_rect, color=None, fill=(15/255, 23/255, 42/255))

    # Header Accent Stripe (Indigo 600)
    stripe_rect = fitz.Rect(0, 136, 595.28, 142)
    page.draw_rect(stripe_rect, color=None, fill=(79/255, 70/255, 229/255))

    # Header Text
    page.insert_text(
        (40, 60),
        "PrintX",
        fontsize=38,
        color=(1, 1, 1),
        fontname="helv"
    )
    page.insert_text(
        (40, 95),
        "SMART SELF-SERVICE PRINTING KIOSK",
        fontsize=14,
        color=(199/255, 210/255, 254/255),
        fontname="helv"
    )
    page.insert_text(
        (40, 118),
        f"Station ID: {kiosk_code}  •  {kiosk_name}",
        fontsize=11,
        color=(148/255, 163/255, 184/255),
        fontname="helv"
    )

    # Headline Section
    page.insert_text(
        (40, 185),
        "Print Directly From Your Smartphone",
        fontsize=24,
        color=(15/255, 23/255, 42/255),
        fontname="helv"
    )
    page.insert_text(
        (40, 210),
        "No app installation, computer login, or USB drives required. Instant UPI checkout.",
        fontsize=12,
        color=(100/255, 116/255, 139/255),
        fontname="helv"
    )

    # QR Code Container Box
    qr_box = fitz.Rect(147, 240, 447, 540)
    page.draw_rect(qr_box, color=(226/255, 232/255, 240/255), fill=(248/255, 250/255, 252/255), width=2)

    # Embed QR Code in center
    qr_embed_rect = fitz.Rect(167, 255, 427, 515)
    page.insert_image(qr_embed_rect, stream=qr_bytes)

    # Scan Prompt below QR
    page.insert_text(
        (190, 532),
        "POINT CAMERA AT QR CODE TO START",
        fontsize=10,
        color=(79/255, 70/255, 229/255),
        fontname="helv"
    )

    # 3-Step Instruction Cards
    steps = [
        ("1. SCAN", "Open camera or QR app and scan this code to access your kiosk portal."),
        ("2. UPLOAD & PAY", "Choose your PDF, select pages & color mode, and pay via any UPI app."),
        ("3. COLLECT PRINTS", "Your single-sided prints exit directly into the HP Smart Tank tray.")
    ]

    card_y = 570
    card_height = 55
    for i, (title, desc) in enumerate(steps):
        rect = fitz.Rect(40, card_y + (i * 68), 555, card_y + (i * 68) + card_height)
        page.draw_rect(rect, color=(226/255, 232/255, 240/255), fill=(255/255, 255/255, 255/255), width=1)

        # Step badge
        badge_rect = fitz.Rect(52, card_y + (i * 68) + 12, 170, card_y + (i * 68) + 42)
        page.draw_rect(badge_rect, color=None, fill=(238/255, 242/255, 255/255))
        page.insert_text((60, card_y + (i * 68) + 31), title, fontsize=11, color=(67/255, 56/255, 202/255), fontname="helv")

        # Step description
        page.insert_text((185, card_y + (i * 68) + 32), desc, fontsize=10, color=(51/255, 65/255, 85/255), fontname="helv")

    # Hardware Specs & Footer Banner
    footer_rect = fitz.Rect(0, 785, 595.28, 841.89)
    page.draw_rect(footer_rect, color=None, fill=(241/255, 245/255, 249/255))

    page.insert_text(
        (40, 808),
        "Hardware: HP Smart Tank 585  •  Paper: Standard A4  •  Single-Sided Simplex",
        fontsize=9,
        color=(100/255, 116/255, 139/255),
        fontname="helv"
    )
    page.insert_text(
        (40, 825),
        "Protected by PrintX Deterministic Spooler Verification & Server-Side Security",
        fontsize=8,
        color=(148/255, 163/255, 184/255),
        fontname="helv"
    )

    out_file = Path(output_path).resolve()
    doc.save(str(out_file))
    doc.close()
    print(f"[+] Kiosk signage poster successfully generated: {out_file} (A4, 1 Page)")
    return str(out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PrintX Kiosk Signage Poster")
    parser.add_argument("--kiosk-code", default="KIOSK-01", help="Kiosk identifier code")
    parser.add_argument("--kiosk-name", default="Campus Central Library Terminal", help="Kiosk display name")
    parser.add_argument("--base-url", default="http://localhost:5173", help="Frontend public URL")
    parser.add_argument("--output", default="kiosk_poster_KIOSK-01.pdf", help="Output PDF file path")
    args = parser.parse_args()

    generate_kiosk_poster(
        kiosk_code=args.kiosk_code,
        kiosk_name=args.kiosk_name,
        base_url=args.base_url,
        output_path=args.output
    )

