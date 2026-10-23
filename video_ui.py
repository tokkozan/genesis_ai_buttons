"""Japanese captions over actual Genesis camera frames."""
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

JAPANESE = {"red": "赤", "green": "緑", "blue": "青"}


@lru_cache(maxsize=16)
def font(size):
    for name in ["/mnt/c/Windows/Fonts/YuGothM.ttc", "C:/Windows/Fonts/YuGothM.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError("Japanese font is unavailable")


def compose(scene, elapsed, status, request, scans, sensor, completed, depth, roi):
    canvas = Image.new("RGB", (1280, 720), "white")
    canvas.paste(Image.fromarray(scene).resize((922, 614)), (0, 106))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1280, 105), fill="#142d3d")
    draw.text((24, 12), "Genesis：AI色認識でSO-101が検査ボタンを操作", font=font(29), fill="white")
    draw.text((24, 61), "講義のシミュレーター Genesis 0.3.3  |  RTX A2000 / WSL2  |  1倍速", font=font(18), fill="#b9d4de")
    draw.rectangle((922, 106, 1280, 720), fill="white")
    draw.text((944, 121), f"経過 {elapsed:05.1f} 秒", font=font(24), fill="#142d3d")
    draw.text((944, 164), "指示：" + " → ".join(JAPANESE[c] for c in request), font=font(21), fill="#142d3d")
    draw.text((944, 204), status, font=font(19), fill="#155d70")
    draw.text((944, 240), f"押下完了：{len(completed)}/3", font=font(20), fill="#142d3d")
    draw.text((944, 276), "初期Genesisカメラ / AI色分類", font=font(16), fill="#455765")
    if sensor is not None:
        canvas.paste(Image.fromarray(sensor).resize((280, 210)), (952, 306))
        x, y = 952 + roi[0] * 280 / 320, 306 + roi[1] * 210 / 240
        draw.rectangle((x-4, y-4, x+4, y+4), outline="white", width=2)
    for i, scan in enumerate(scans):
        draw.text((944, 530+28*i), f"地点{scan['station']}：{JAPANESE[scan['prediction']]}  確率{scan['probability']:.1%}", font=font(17), fill="#142d3d")
    draw.text((944, 625), f"接触による押し込み：{depth*1000:.1f} mm", font=font(17), fill="#155d70")
    draw.text((944, 659), "物理・接触・カメラ：Genesis", font=font(17), fill="#455765")
    draw.rounded_rectangle((20, 658, 860, 704), radius=5, fill="#142d3d")
    draw.text((35, 669), "先端の接触＋ボタンの4mm以上の沈み込みで押下成功。色の指示に従って操作。", font=font(18), fill="white")
    return np.asarray(canvas)
