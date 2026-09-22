"""Measure how much of a QR code you can destroy before it stops scanning.

Three damage models, because the answer depends far more on WHERE than HOW MUCH:
  sticker  a contiguous patch, like a label or a coffee ring
  speckle  scattered single-module flips, like dirt or print noise
  targeted a specific structural feature (finder, timing, format)

Run: python damage.py
"""
import random
import cv2
import numpy as np
import segno

PAYLOAD = "https://example.com/hello"
SCALE, BORDER = 10, 4
det = cv2.QRCodeDetector()


def base(ec):
    # boost_error=False matters: segno otherwise silently upgrades the level
    q = segno.make(PAYLOAD, error=ec, boost_error=False)
    return np.array([list(r) for r in q.matrix], np.uint8), q


def to_image(mat):
    n = mat.shape[0]
    big = np.kron(1 - mat, np.ones((SCALE, SCALE), np.uint8)) * 255
    out = np.full(((n + 2 * BORDER) * SCALE,) * 2, 255, np.uint8)
    o = BORDER * SCALE
    out[o:o + n * SCALE, o:o + n * SCALE] = big
    return out


def decodes(mat):
    data, _, _ = det.detectAndDecode(to_image(mat))
    return data == PAYLOAD


def sticker(mat, frac, rng, keep_clear=9):
    m = mat.copy()
    n = m.shape[0]
    side = max(1, int(round((frac * n * n) ** 0.5)))
    if side >= n - keep_clear:
        return np.zeros_like(m)
    r = rng.randint(keep_clear, n - side)
    c = rng.randint(keep_clear, n - side)
    m[r:r + side, c:c + side] = 0
    return m


def speckle(mat, frac, rng):
    m = mat.copy()
    n = m.shape[0]
    for i in rng.sample(range(n * n), int(round(frac * n * n))):
        m[i // n, i % n] ^= 1
    return m


if __name__ == "__main__":
    for name, fn, fracs in (("sticker over data", sticker, [.05, .10, .15, .20, .25]),
                            ("scattered speckle", speckle, [.01, .02, .03, .05])):
        print(f"\n{name} — % of 200 attempts that still decoded")
        print("  EC  " + "".join(f"{int(f*100):>7}%" for f in fracs))
        for ec in "lmqh":
            mat, _ = base(ec)
            rng = random.Random(21)
            row = [sum(decodes(fn(mat, f, rng)) for _ in range(200)) / 200 for f in fracs]
            print(f"  {ec.upper():<3} " + "".join(f"{v*100:>7.1f} " for v in row))

    print("\ntargeted structural damage")
    for ec in ("l", "h"):
        mat, _ = base(ec)
        n = mat.shape[0]
        for label, (rs, cs) in {
            "one finder pattern": (slice(0, 7), slice(0, 7)),
            "half the timing row": (slice(6, 7), slice(8, n // 2)),
            "format strip": (slice(8, 9), slice(0, 9)),
        }.items():
            m = mat.copy()
            m[rs, cs] = 0
            pct = 100 * ((rs.stop - rs.start) * (cs.stop - cs.start)) / (n * n)
            print(f"  EC={ec.upper()} {label:<22}{pct:>5.1f}% -> "
                  f"{'decodes' if decodes(m) else 'DEAD'}")
