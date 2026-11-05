"""
Simple, one-message versions of the two bonus images, for the submission form.
(The detailed versions are made by 04_what_it_saw.py and 05_where_it_walked.py.)

Usage:  python scripts/06_form_images.py
Output: results/form/what_it_saw.png, results/form/where_it_walked.png
"""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from PIL import Image

from common import ALERT, INK, MUTED, OK, RESULTS, SEQUENCE, connect, load_answer, stream, style, utc_hms

OUT = RESULTS / "form"


def what_it_saw(seq, ans, t0):
    fall_s, fall_e = ans["start_ns"], ans["end_ns"]
    frames = [(m.timestamp_ns, Image.open(BytesIO(m.data.data)).convert("RGB"))
              for m in stream(seq, "/camera/front/image", fall_s - 400_000_000, fall_e + 400_000_000)]
    hero = next(i for i, (t, _) in enumerate(frames) if fall_s <= t <= fall_e)
    strip = frames[max(0, hero - 2):hero + 3]
    rel = lambda ns: (ns - t0) / 1e9

    fig = plt.figure(figsize=(10, 9.6), dpi=150)
    gs = fig.add_gridspec(2, len(strip), height_ratios=[4.2, 1.0], hspace=0.12, wspace=0.05,
                          left=0.04, right=0.96, top=0.87, bottom=0.04)
    fig.text(0.04, 0.95, "What spot-07 saw during the free fall", fontsize=20, weight="bold", color=INK)
    fig.text(0.04, 0.913, f"Front camera  ·  t+{rel(frames[hero][0]):.3f} s  ·  {utc_hms(frames[hero][0])} UTC  ·  "
             f"the only frame captured while airborne", fontsize=11.5, color=MUTED)

    ax = fig.add_subplot(gs[0, :])
    ax.imshow(frames[hero][1], interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_color(ALERT); s.set_linewidth(4)

    for j, (t, im) in enumerate(strip):
        ax = fig.add_subplot(gs[1, j])
        ax.imshow(im); ax.set_xticks([]); ax.set_yticks([])
        inside = fall_s <= t <= fall_e
        for s in ax.spines.values():
            s.set_visible(True); s.set_color(ALERT if inside else "#d1d5db"); s.set_linewidth(3 if inside else 1)
        ax.set_xlabel(f"t+{rel(t):.3f} s", fontsize=9.5, color=ALERT if inside else MUTED,
                      weight="bold" if inside else "normal")

    out = OUT / "what_it_saw.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def where_it_walked(seq, ans, t0):
    fall_s = ans["start_ns"]
    odom = np.array([(m.timestamp_ns, m.data.pose.position.x, m.data.pose.position.y)
                     for m in stream(seq, "/robot/odom")], dtype=np.float64)
    t = (odom[:, 0] - t0) / 1e9
    x, y = odom[:, 1], odom[:, 2]
    dist = float(np.sum(np.hypot(np.diff(x), np.diff(y))))
    k = int(np.searchsorted(odom[:, 0], fall_s))

    fig = plt.figure(figsize=(14, 6.4), dpi=150)
    ax = fig.add_axes([0.05, 0.1, 0.86, 0.72])
    fig.text(0.05, 0.92, "Where spot-07 walked: the patrol spells MOSAICO", fontsize=20, weight="bold", color=INK)
    fig.text(0.05, 0.865, f"Odometry  ·  {dist:.1f} m in {t[-1]:.1f} s  ·  "
             f"★ free fall at t+{(fall_s - t0) / 1e9:.3f} s, on the “A”", fontsize=12, color=MUTED)

    pts = np.column_stack([x, y]).reshape(-1, 1, 2)
    lc = LineCollection(np.concatenate([pts[:-1], pts[1:]], axis=1), cmap="viridis", linewidth=3.4,
                        capstyle="round")
    lc.set_array(t[:-1])
    ax.add_collection(lc)
    cax = fig.add_axes([0.925, 0.1, 0.012, 0.72])
    cb = fig.colorbar(lc, cax=cax)
    cb.set_label("time (s)", color=MUTED)

    ax.plot(x[0], y[0], "o", ms=12, color=OK, mec="white", mew=2, zorder=5)
    ax.annotate("start", (x[0], y[0]), xytext=(10, -14), textcoords="offset points", fontsize=11, color=OK,
                weight="bold")
    ax.plot(x[-1], y[-1], "s", ms=11, color=INK, mec="white", mew=2, zorder=5)
    ax.annotate("end", (x[-1], y[-1]), xytext=(10, -14), textcoords="offset points", fontsize=11, color=INK,
                weight="bold")
    ax.plot(x[k], y[k], marker="*", ms=30, color=ALERT, mec="white", mew=1.5, zorder=6)
    ax.annotate(f"free fall\n{utc_hms(fall_s)} UTC", (x[k], y[k]), xytext=(x[k] + 0.9, y[k] + 1.3),
                fontsize=11.5, color=ALERT, weight="bold", arrowprops=dict(arrowstyle="->", color=ALERT, lw=1.5))

    ax.set_aspect("equal")
    ax.set_xlim(x.min() - 0.7, x.max() + 0.9)
    ax.set_ylim(y.min() - 0.7, y.max() + 1.8)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    out = OUT / "where_it_walked.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> None:
    ans = load_answer()
    style(plt)
    OUT.mkdir(parents=True, exist_ok=True)
    with connect() as client:
        seq = client.sequence_handler(SEQUENCE)
        t0 = seq.timestamp_ns_min
        for path in (what_it_saw(seq, ans, t0), where_it_walked(seq, ans, t0)):
            print(f"Saved {path}")


if __name__ == "__main__":
    main()
