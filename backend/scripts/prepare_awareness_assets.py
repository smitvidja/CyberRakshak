"""Convert the awareness poster source art into web-ready assets.

The originals in demo-assets/Resources/ are ~2MB PNGs (and the logo sits on a
large white canvas). Serving those directly would make the Resources page crawl,
so this produces WebP versions in frontend/public/images/awareness/ at a sensible
display size, and crops the logo to its actual content.

Originals stay in demo-assets/ as the source of truth - re-run this after
replacing any of them.

Usage (from the backend/ directory, with the project virtualenv active):
    python scripts/prepare_awareness_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "demo-assets" / "Resources"
DEST = ROOT / "frontend" / "public" / "images" / "awareness"

# Source file -> published slug. "Fake Job Offer" is deliberately excluded: the
# body text inside its mock offer letter is unreadable AI gibberish, and the
# prepaid-task poster already covers job-scam ground. "Long - SIM Swap Fraud" is
# a wide duplicate of the portrait SIM-swap poster.
POSTERS = {
    "Identity Theft.png": "identity-theft",
    "Loan App Harassment.png": "loan-app-harassment",
    "Matrimonial Scam.png": "matrimonial-scam",
    "Misinformation.png": "misinformation",
    "Prepaid Task Scam.png": "prepaid-task-scam",
    "QR Code - UPI Scam.png": "qr-upi-scam",
    "SIM Swap Fraud.png": "sim-swap-fraud",
    "The First Hour After Fraud.png": "first-hour-after-fraud",
    "Webcam Blackmail.png": "webcam-blackmail",
    "Long - OTP Fraud.png": "otp-remote-access",
}

MAX_WIDTH = 900
QUALITY = 82


def _trim_white(image: Image.Image, threshold: int = 24) -> Image.Image:
    """Crop a logo down to its actual mark, dropping the white canvas around it.

    A plain difference-based bbox keeps every faintly off-white anti-aliased pixel,
    which leaves a wide margin around the mark. Thresholding first means only
    genuinely inked pixels define the bounding box.
    """
    rgb = image.convert("RGB")
    background = Image.new("RGB", rgb.size, (255, 255, 255))
    difference = ImageChops.difference(rgb, background).convert("L")
    mask = difference.point(lambda value: 255 if value > threshold else 0)
    bbox = mask.getbbox()
    return image.crop(bbox) if bbox else image


def prepare() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    total_before = 0
    total_after = 0

    for file_name, slug in POSTERS.items():
        source = SOURCE / file_name
        if not source.exists():
            print(f"MISSING  {file_name} - skipped")
            continue
        image = Image.open(source).convert("RGB")
        if image.width > MAX_WIDTH:
            height = round(image.height * MAX_WIDTH / image.width)
            image = image.resize((MAX_WIDTH, height), Image.LANCZOS)
        destination = DEST / f"{slug}.webp"
        image.save(destination, "WEBP", quality=QUALITY, method=6)

        before = source.stat().st_size
        after = destination.stat().st_size
        total_before += before
        total_after += after
        print(
            f"{slug:<24} {image.width}x{image.height}  "
            f"{before / 1024 / 1024:.1f}MB -> {after / 1024:.0f}KB"
        )

    logo_source = SOURCE / "Logo.png"
    if logo_source.exists():
        logo = _trim_white(Image.open(logo_source).convert("RGB"))
        # Small even padding so the mark doesn't sit flush against the edge.
        side = round(max(logo.size) * 1.06)
        square = Image.new("RGB", (side, side), (255, 255, 255))
        square.paste(logo, ((side - logo.width) // 2, (side - logo.height) // 2))
        square = square.resize((320, 320), Image.LANCZOS)
        # Filename carries a version suffix on purpose. Browsers (and Next.js's image
        # optimizer) cache aggressively by URL, so replacing the art at a stable path
        # left people staring at the previous logo until they hard-refreshed. Bump the
        # suffix whenever the mark itself changes so the URL changes with it.
        logo_destination = DEST / "logo-v2.webp"
        square.save(logo_destination, "WEBP", quality=90, method=6)
        print(
            f"{'logo':<24} 320x320  "
            f"{logo_source.stat().st_size / 1024 / 1024:.1f}MB -> "
            f"{logo_destination.stat().st_size / 1024:.0f}KB"
        )
    else:
        print("MISSING  Logo 2.png - skipped")

    if total_before:
        print(
            f"\nposters: {total_before / 1024 / 1024:.1f}MB -> "
            f"{total_after / 1024 / 1024:.2f}MB "
            f"({100 - total_after / total_before * 100:.0f}% smaller)"
        )


if __name__ == "__main__":
    prepare()
