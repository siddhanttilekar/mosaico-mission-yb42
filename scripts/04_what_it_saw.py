"""
Bonus 1 - What the robot saw.

Uses the free-fall window from step 2 to slice the front camera and the IMU
*server-side* in Mosaico, then builds one figure:
  - the camera frame captured while spot-07 was airborne (large)
  - a filmstrip of the frames just before and after
  - vertical acceleration around the event, with the mission log overlaid

Usage:  python scripts/04_what_it_saw.py
Output: results/what_it_saw.png
"""

from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from common import ALERT, INK, MUTED, RESULTS, SEQUENCE, connect, imu_z, load_answer, mission_log, stream, style, utc_hms

CAMERA = "/camera/front/image"
FILMSTRIP = 7                 # frames shown in the strip (odd: fall frame in the middle)
TIMELINE = (-3.0, 3.0)        # seconds around the fall start shown in the IMU plot


def main() -> None:
    ans = load_answer()
    fall_s, fall_e = ans["start_ns"], ans["end_ns"]

    with connect() as client:
        seq = client.sequence_handler(SEQUENCE)
        t0 = seq.timestamp_ns_min
        # Only the camera frames around the event are pulled from Mosaico
        frames = [(m.timestamp_ns, Image.open(BytesIO(m.data.data)).convert("RGB"))
                  for m in stream(seq, CAMERA, fall_s - 1_000_000_000, fall_e + 1_000_000_000)]
        imu_t, imu_az = imu_z(seq, fall_s + TIMELINE[0] * 1e9, fall_s + TIMELINE[1] * 1e9)
        log = mission_log(seq)

    rel = lambda ns: (ns - t0) / 1e9
    airborne = [i for i, (t, _) in enumerate(frames) if fall_s <= t <= fall_e]
    if not airborne:
        raise SystemExit("No camera frame inside the free-fall window.")
    hero = airborne[0]
    lo = max(0, hero - FILMSTRIP // 2)
    strip = frames[lo:lo + FILMSTRIP]

    style(plt)
    fig = plt.figure(figsize=(16, 10.5), dpi=150)
    gs = fig.add_gridspec(3, FILMSTRIP, height_ratios=[3.1, 1.15, 1.6], hspace=0.32, wspace=0.06,
                          left=0.04, right=0.98, top=0.88, bottom=0.07)

    fig.text(0.04, 0.955, "What spot-07 saw while it was in free fall", fontsize=22, weight="bold", color=INK)
    fig.text(0.04, 0.922,
             f"Front camera, sequence '{SEQUENCE}'  ·  free fall {utc_hms(fall_s)} → {utc_hms(fall_e)} UTC "
             f"({ans['duration_ms']:.0f} ms)  ·  all data sliced server-side from Mosaico",
             fontsize=12, color=MUTED)

    # --- hero frame -----------------------------------------------------------
    ax = fig.add_subplot(gs[0, :4])
    t_hero, img = frames[hero]
    ax.imshow(img, interpolation="bilinear")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(True); s.set_color(ALERT); s.set_linewidth(4)
    ax.set_title(f"t+{rel(t_hero):.3f} s  ·  {utc_hms(t_hero)} UTC  ·  the only frame captured mid-air",
                 fontsize=12, color=ALERT, weight="bold", loc="left")

    # --- findings panel -----------------------------------------------------------
    ax = fig.add_subplot(gs[0, 4:]); ax.axis("off")
    log_lines = [(rel(t), txt) for t, txt in log if -4 <= rel(t) - rel(fall_s) <= 4]
    findings = [
        ("Free fall", f"t+{rel(fall_s):.3f} s → t+{rel(fall_e):.3f} s, {ans['duration_ms']:.0f} ms"),
        ("Start (ns)", f"{fall_s}"),
        ("In view", "a “DON'T PANIC” sign beside a pink crate"),
        ("Frames in the air", f"{len(airborne)} of {len(frames)} frames in ±1 s (camera ≈ 8 fps)"),
    ]
    y = 0.98
    ax.text(0, y, "Findings", fontsize=15, weight="bold", color=INK, va="top", transform=ax.transAxes)
    y -= 0.11
    for k, v in findings:
        ax.text(0, y, k, fontsize=11, color=MUTED, va="top", transform=ax.transAxes)
        ax.text(0.36, y, v, fontsize=11, color=INK, va="top", transform=ax.transAxes, wrap=True)
        y -= 0.085
    y -= 0.04
    ax.text(0, y, "Mission log around the event", fontsize=15, weight="bold", color=INK, va="top", transform=ax.transAxes)
    y -= 0.1
    for t, txt in log_lines:
        warn = "[WARN]" in txt or "recovered" in txt
        ax.text(0, y, f"t+{t:6.2f} s", fontsize=10.5, color=MUTED, va="top", family="DejaVu Sans Mono", transform=ax.transAxes)
        ax.text(0.2, y, txt, fontsize=10.5, color=ALERT if warn else INK, va="top", transform=ax.transAxes)
        y -= 0.075
    ax.text(0, max(y - 0.03, 0.0),
            "The operator's log never mentions a fall: it calls it an “IMU transient”, 1.8 s later.",
            fontsize=10.5, style="italic", color=MUTED, va="top", transform=ax.transAxes)

    # --- filmstrip --------------------------------------------------------------
    for j, (t, im) in enumerate(strip):
        ax = fig.add_subplot(gs[1, j])
        ax.imshow(im); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        inside = fall_s <= t <= fall_e
        for s in ax.spines.values():
            s.set_visible(True); s.set_color(ALERT if inside else "#d1d5db"); s.set_linewidth(3 if inside else 1)
        ax.set_title(f"t+{rel(t):.3f} s" + ("  ✈ airborne" if inside else ""), fontsize=9.5,
                     color=ALERT if inside else MUTED, weight="bold" if inside else "normal")

    # --- IMU timeline ---------------------------------------------------------------
    ax = fig.add_subplot(gs[2, :])
    tt = [(t - t0) / 1e9 for t in imu_t]
    ax.plot(tt, imu_az, color=INK, lw=1.0, label="IMU vertical acceleration (z)")
    top = max(imu_az) * 1.28
    ax.set_xlim(tt[0], tt[-1])
    ax.set_ylim(-9, top)
    ax.axhspan(-1, 1, color=ALERT, alpha=0.07, lw=0)
    ax.axvspan(rel(fall_s), rel(fall_e), color=ALERT, alpha=0.25, lw=0)
    ax.axhline(9.81, color=MUTED, lw=0.8, ls=":")
    ax.text(tt[-1] - 0.03, 9.81, "1 g ", fontsize=9, color=MUTED, ha="right", va="bottom",
            bbox=dict(fc="white", ec="none", pad=1))
    ax.annotate(f"free fall: |a_z| ≤ 1 m/s²\nstart {fall_s} ns", xy=(rel(fall_s), 0), xytext=(rel(fall_s) - 2.3, -7.5),
                fontsize=10, color=ALERT, weight="bold", arrowprops=dict(arrowstyle="->", color=ALERT))
    i_peak = max(range(len(imu_az)), key=lambda i: imu_az[i] if tt[i] > rel(fall_e) else -1e9)
    ax.annotate(f"landing ≈ {imu_az[i_peak] / 9.81:.1f} g", xy=(tt[i_peak], imu_az[i_peak]),
                xytext=(tt[i_peak] + 0.15, imu_az[i_peak] - 1), fontsize=9.5, color=INK)
    # camera frame instants, as ticks along the top edge
    for t, _ in frames:
        ax.axvline(rel(t), ymin=0.93, ymax=1.0, color=MUTED, lw=0.6)
    ax.text(rel(frames[0][0]) - 0.04, top * 0.965, "camera frames", fontsize=9, color=MUTED, ha="right", va="center")
    # mission-log warnings as labelled dashed lines
    short = {"towel": "“towel?”", "transient": "“IMU transient”", "recovered": "“recovered”"}
    for t, txt in log:
        if tt[0] <= rel(t) <= tt[-1] and ("WARN" in txt or "recovered" in txt):
            ax.axvline(rel(t), ymax=0.9, color=ALERT, lw=0.9, ls="--", alpha=0.6)
            label = next((v for k, v in short.items() if k in txt), "log")
            ax.text(rel(t) + 0.03, top * 0.80, label, fontsize=9, color=ALERT, ha="left")
    ax.set_xlabel("seconds since mission start")
    ax.set_ylabel("a_z  [m/s²]")
    ax.legend(loc="lower right", frameon=False, fontsize=9.5)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "what_it_saw.png"
    fig.savefig(out)
    print(f"Saved {out}  (hero frame t+{rel(t_hero):.3f}s, {len(airborne)} airborne frame(s))")


if __name__ == "__main__":
    main()
