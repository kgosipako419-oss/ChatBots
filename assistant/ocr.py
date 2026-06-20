"""On-screen text recognition (OCR) via RapidOCR — the fallback "eyes" for apps
that don't expose accessibility info (images, games, some web/Electron apps).
"""
from __future__ import annotations

from typing import Optional

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR  # downloads small models on first use
        _engine = RapidOCR()
    return _engine


def ocr_array(np_img) -> list[dict]:
    """Run OCR on an RGB numpy image. Returns [{text, score, center, box}]."""
    engine = _get_engine()
    result, _elapse = engine(np_img)
    items: list[dict] = []
    for box, text, score in (result or []):
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({
            "text": text,
            "score": float(score),
            "center": (sum(xs) / len(xs), sum(ys) / len(ys)),
            "top": min(ys),
        })
    return items


def screen_items(region: Optional[tuple] = None) -> list[dict]:
    """OCR the whole screen (or a region: left, top, width, height)."""
    import numpy as np
    import pyautogui
    img = pyautogui.screenshot(region=region)
    return ocr_array(np.array(img))


def screen_text(region: Optional[tuple] = None) -> str:
    """Return on-screen text in roughly reading order (top to bottom)."""
    items = screen_items(region)
    items.sort(key=lambda it: it["top"])
    return " ".join(it["text"] for it in items).strip()
