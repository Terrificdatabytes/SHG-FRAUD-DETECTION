#!/usr/bin/env python
"""Render the two animated explainer diagrams used on the 'How it works' page.

Outputs: assets/how_it_works.gif and assets/diversion_vs_genuine.gif
Pure Pillow, no emoji, no external assets. Re-run to regenerate.
"""
import math, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"; OUT.mkdir(exist_ok=True)
S = 2  # supersampling factor

INK, MUTED, LINE, BG = (15, 23, 42), (100, 116, 139), (226, 232, 240), (248, 250, 252)
ACC, ACC_SOFT = (79, 70, 229), (238, 242, 255)
OK, WARN, BAD = (5, 150, 105), (217, 119, 6), (220, 38, 38)
WHITE = (255, 255, 255)


def font(weight, size):
    cands = {
        "r": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "DejaVuSans.ttf"],
        "b": ["/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"],
    }[weight]
    try:
        import matplotlib
        base = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        cands += [str(base / ("DejaVuSans.ttf" if weight == "r" else "DejaVuSans-Bold.ttf"))]
    except Exception:
        pass
    for c in cands:
        try:
            return ImageFont.truetype(c, size * S)
        except Exception:
            continue
    return ImageFont.load_default()


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ease(t):
    return t * t * (3 - 2 * t)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.im = Image.new("RGB", (w * S, h * S), BG)
        self.d = ImageDraw.Draw(self.im)

    def rr(self, box, r, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = [v * S for v in box]
        self.d.rounded_rectangle([x0, y0, x1, y1], r * S, fill=fill, outline=outline, width=width * S)

    def circle(self, c, r, fill=None, outline=None, width=1):
        x, y = c[0] * S, c[1] * S
        self.d.ellipse([x - r * S, y - r * S, x + r * S, y + r * S], fill=fill, outline=outline, width=width * S)

    def line(self, pts, fill, width=2):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(width * S), joint="curve")

    def text(self, xy, s, f, fill=INK, anchor="la"):
        self.d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)

    def arrow(self, pts, fill, width=2, head=9):
        self.line(pts, fill, width)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        a = math.atan2(y1 - y0, x1 - x0)
        p = [(x1, y1), (x1 - head * math.cos(a - .45), y1 - head * math.sin(a - .45)),
             (x1 - head * math.cos(a + .45), y1 - head * math.sin(a + .45))]
        self.d.polygon([(x * S, y * S) for x, y in p], fill=fill)

    def done(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def along(pts, t):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tot = sum(seg); d = t * tot
    for i, s in enumerate(seg):
        if d <= s or i == len(seg) - 1:
            u = 0 if s == 0 else min(d / s, 1)
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)
        d -= s


def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


# ----------------------------------------------------------------- icons
def icon(c, kind, cx, cy, col):
    s = 1
    if kind == "doc":
        c.rr((cx - 13, cy - 17, cx + 13, cy + 17), 3, outline=col, width=3)
        for i in range(4): c.line([(cx - 7, cy - 8 + i * 7), (cx + 7, cy - 8 + i * 7)], col, 2)
    elif kind == "lock":
        c.rr((cx - 14, cy - 3, cx + 14, cy + 16), 3, fill=col)
        c.d.arc([(cx - 9) * S, (cy - 19) * S, (cx + 9) * S, (cy + 1) * S], 180, 360, fill=col, width=3 * S)
        c.circle((cx, cy + 6), 3, fill=WHITE)
    elif kind == "graph":
        pts = [(cx - 14, cy + 9), (cx, cy - 12), (cx + 14, cy + 9), (cx + 1, cy + 14)]
        for a, b in ((0, 1), (1, 2), (0, 3), (2, 3)): c.line([pts[a], pts[b]], col, 2)
        for p in pts: c.circle(p, 5, fill=col)
    elif kind == "loop":
        c.d.arc([(cx - 15) * S, (cy - 15) * S, (cx + 15) * S, (cy + 15) * S], 30, 330, fill=col, width=3 * S)
        c.arrow([(cx + 8, cy - 14), (cx + 15, cy - 6)], col, 3, 8)
    elif kind == "gauge":
        c.d.arc([(cx - 17) * S, (cy - 15) * S, (cx + 17) * S, (cy + 19) * S], 180, 360, fill=col, width=4 * S)
        c.line([(cx, cy + 3), (cx + 9, cy - 8)], col, 3); c.circle((cx, cy + 3), 3, fill=col)
    elif kind == "person":
        c.circle((cx, cy - 8), 7, fill=col)
        c.d.pieslice([(cx - 14) * S, (cy + 2) * S, (cx + 14) * S, (cy + 30) * S], 180, 360, fill=col)
    elif kind == "check":
        c.line([(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 8)], col, 4)


# ----------------------------------------------------------------- GIF 1
def how_it_works():
    W, H = 1200, 450
    steps = [
        ("1", "Upload", "Transaction report plus applicant consent", "doc"),
        ("2", "Protect privacy", "Names and numbers become secret codes", "lock"),
        ("3", "Map the money", "Every transfer becomes a link between accounts", "graph"),
        ("4", "Find patterns", "Fast pass-through and return loops are measured", "loop"),
        ("5", "Score the risk", "Model gives a risk % with a confidence range", "gauge"),
        ("6", "Human review", "Officer verifies in the field. No automatic rejection", "person"),
    ]
    bw, gap, x0, y0, bh = 170, 28, 20, 100, 215
    fT, fS, fN, fBig, fSm = font("b", 17), font("r", 13), font("b", 13), font("b", 22), font("r", 14)
    frames, per = [], 10
    n = len(steps)
    for f in range(n * per):
        active, t = divmod(f, per); t /= per
        c = Canvas(W, H)
        c.text((20, 18), "From a transaction report to a human decision, in six steps", font("b", 22), INK)
        c.text((20, 52), "Each step is shown in order. The highlighted box is the one running now.", fSm, MUTED)
        for i, (num, ttl, sub, ic) in enumerate(steps):
            x = x0 + i * (bw + gap)
            on, past = i == active, i < active
            fill = WHITE; outline = ACC if on else LINE
            if on: c.rr((x - 3, y0 - 3, x + bw + 3, y0 + bh + 3), 16, fill=ACC_SOFT)
            c.rr((x, y0, x + bw, y0 + bh), 14, fill=fill, outline=outline, width=2 if on else 1)
            col = ACC if (on or past) else (148, 163, 184)
            c.circle((x + 24, y0 + 24), 13, fill=col)
            c.text((x + 24, y0 + 24), num, fN, WHITE, "mm")
            icon(c, ic, x + bw // 2, y0 + 74, col)
            c.text((x + bw // 2, y0 + 118), ttl, fT, INK if (on or past) else MUTED, "ma")
            # wrap subtitle
            words, lines, cur = sub.split(), [], ""
            for w in words:
                trial = (cur + " " + w).strip()
                if fS.getlength(trial) / S > bw - 24 and cur: lines.append(cur); cur = w
                else: cur = trial
            lines.append(cur)
            for k, ln in enumerate(lines[:4]): c.text((x + bw // 2, y0 + 146 + k * 18), ln, fS, MUTED, "ma")
            if i < n - 1:
                ax0, ax1, ay = x + bw + 4, x + bw + gap - 4, y0 + bh // 2
                c.arrow([(ax0, ay), (ax1, ay)], ACC if past else LINE, 2, 7)
        # travelling packet
        if active < n - 1 and t > 0.25:
            xa = x0 + active * (bw + gap) + bw + 4; xb = xa + gap - 8
            px = xa + (xb - xa) * ease((t - .25) / .75); c.circle((px, y0 + bh // 2), 6, fill=ACC)
        # progress + caption
        c.rr((20, 360, W - 20, 366), 3, fill=LINE)
        c.rr((20, 360, 20 + (W - 40) * (active + t) / n, 366), 3, fill=ACC)
        num, ttl, sub, _ = steps[active]
        c.text((20, 386), f"Step {num} of {n}:  {ttl}", fBig, INK)
        c.text((20, 418), sub, font("r", 15), MUTED)
        frames.append(c.done())
    save(frames, OUT / "how_it_works.gif", 130)


# ----------------------------------------------------------------- GIF 2
def node(c, cx, cy, label, sub, kind="plain", col=ACC, glow=0.0):
    w, h = 132, 62
    if glow > 0: c.rr((cx - w / 2 - 5, cy - h / 2 - 5, cx + w / 2 + 5, cy + h / 2 + 5), 16, fill=mix(WHITE, col, .25 * glow))
    c.rr((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 12, fill=WHITE, outline=col if kind != "plain" else (148, 163, 184), width=2)
    c.text((cx, cy - 8), label, font("b", 15), INK, "mm")
    c.text((cx, cy + 13), sub, font("r", 12), MUTED, "mm")


def coin(c, p, label, col):
    c.circle(p, 9, fill=col); c.text((p[0], p[1] - 22), label, font("b", 13), col, "mm")


def diversion():
    W, H = 1200, 566
    N = 64
    # lane geometry
    yA, yB = 172, 418
    A = {"bank": (110, yA), "mem": (370, yA), "s1": (700, yA - 76), "s2": (700, yA), "s3": (700, yA + 76)}
    B = {"bank": (110, yB), "mem": (370, yB), "out": (650, yB), "rel": (910, yB)}
    loop = bezier((B["rel"][0], B["rel"][1] + 33), (640, yB + 135), (B["mem"][0], B["mem"][1] + 33))
    frames = []
    for f in range(N):
        c = Canvas(W, H); p = f / (N - 1)
        c.text((20, 16), "What a genuine loan looks like, compared with a diverted loan", font("b", 22), INK)
        # lane cards
        c.rr((20, 54, W - 20, 292), 14, fill=WHITE, outline=LINE)
        c.rr((20, 316, W - 20, 548), 14, fill=WHITE, outline=LINE)
        c.text((40, 68), "Genuine member", font("b", 15), OK)
        c.text((40, 330), "Diversion pattern", font("b", 15), BAD)
        # phases: 0-.2 loan, .2-.55 onward payments, .55-.8 return(B), .8-1 verdict
        def ph(a, b): return max(0, min(1, (p - a) / (b - a)))
        # ---- lane A
        for k in ("s1", "s2", "s3"):
            c.arrow([(A["mem"][0] + 68, A["mem"][1]), (A[k][0] - 70, A[k][1])], (148, 163, 184), 2, 8)
        node(c, *A["bank"], "Bank", "pays loan", col=ACC); node(c, *A["mem"], "Member", "Rs 50,000 in", col=ACC)
        node(c, *A["s1"], "Seed shop", "Rs 20,000", col=OK); node(c, *A["s2"], "Tool seller", "Rs 18,000", col=OK); node(c, *A["s3"], "Labour", "Rs 12,000", col=OK)
        c.arrow([(A["bank"][0] + 68, yA), (A["mem"][0] - 68, yA)], (148, 163, 184), 2, 8)
        t1 = ph(0, .2)
        if 0 < t1 < 1: coin(c, along([(A["bank"][0] + 68, yA), (A["mem"][0] - 68, yA)], t1), "Rs 50,000", ACC)
        t2 = ph(.22, .55)
        if 0 < t2 < 1:
            for i, k in enumerate(("s1", "s2", "s3")):
                tt = max(0, min(1, t2 * 1.3 - i * .12))
                if 0 < tt < 1: coin(c, along([(A["mem"][0] + 68, yA), (A[k][0] - 70, A[k][1])], tt), "", OK)
        # ---- lane B
        node(c, *B["bank"], "Bank", "pays loan", col=ACC); node(c, *B["mem"], "Member", "Rs 50,000 in", col=ACC)
        node(c, *B["out"], "Outside account", "unknown to the group", col=BAD, glow=ph(.3, .5) * (1 if p < .9 else 0.6))
        node(c, *B["rel"], "Third party", "keeps most of it", col=BAD)
        for a, b in (("bank", "mem"), ("mem", "out"), ("out", "rel")):
            c.arrow([(B[a][0] + 68, yB), (B[b][0] - 68, yB)], (148, 163, 184), 2, 8)
        t = ph(0, .2)
        if 0 < t < 1: coin(c, along([(B["bank"][0] + 68, yB), (B["mem"][0] - 68, yB)], t), "Rs 50,000", ACC)
        t = ph(.22, .38)
        if 0 < t < 1: coin(c, along([(B["mem"][0] + 68, yB), (B["out"][0] - 68, yB)], t), "within 72 hours", BAD)
        t = ph(.4, .55)
        if 0 < t < 1: coin(c, along([(B["out"][0] + 68, yB), (B["rel"][0] - 68, yB)], t), "Rs 48,000", BAD)
        # return loop
        lp = ph(.55, .8)
        c.line(loop, mix(LINE, BAD, min(1, lp * 2)), 3)
        c.arrow(loop[-3:], mix(LINE, BAD, min(1, lp * 2)), 3, 11)
        if 0 < lp < 1:
            coin(c, along(loop, lp), "small returns", BAD)
        if lp >= 1:
            pulse = .5 + .5 * math.sin((p - .8) * 40)
            c.text((640, yB + 102), "Return loop detected", font("b", 16), mix(BAD, (255, 120, 120), pulse), "mm")
        # verdicts
        v = ph(.82, .92)
        if v > 0:
            c.rr((930, 135, 1180, 213), 12, fill=mix(WHITE, OK, .12 + .1 * v), outline=OK, width=2)
            c.text((1055, 161), "LOW RISK", font("b", 20), OK, "mm"); c.text((1055, 188), "Spread across real suppliers", font("r", 13), INK, "mm")
            c.rr((930, 362, 1180, 440), 12, fill=mix(WHITE, BAD, .12 + .1 * v), outline=BAD, width=2) if False else None
        if v > 0:
            c.rr((960, 452, 1180, 527), 12, fill=mix(WHITE, BAD, .12 + .1 * v), outline=BAD, width=2)
            c.text((1070, 477), "HIGH RISK", font("b", 20), BAD, "mm"); c.text((1070, 504), "Loan hold, field visit", font("r", 13), INK, "mm")
        frames.append(c.done())
    save(frames, OUT / "diversion_vs_genuine.gif", 110)


def save(frames, path, ms):
    pal = [fr.quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE) for fr in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=[ms] * len(frames), loop=0, optimize=True, disposal=2)
    print("wrote", path, round(os.path.getsize(path) / 1e3), "KB,", len(frames), "frames")


if __name__ == "__main__":
    how_it_works(); diversion()
