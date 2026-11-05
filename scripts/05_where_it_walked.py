"""
Bonus 2 - Where the robot walked.

Streams the full odometry track from Mosaico and plots spot-07's patrol of
Yard B, marking where the free fall happened (window from step 2), the
waypoint groups from the mission log, and - as physical proof that the robot
was airborne - the four foot load cells around the event.

Usage:  python scripts/05_where_it_walked.py
Output: results/where_it_walked.png
"""

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

from common import (ALERT, INK, MUTED, OK, RESULTS, SEQUENCE, connect, imu_z, load_answer, mission_log, stream,
                    style, utc_hms)

FEET = ["FL", "FR", "HL", "HR"]
FEET_NAMES = {"FL": "front-left", "FR": "front-right", "HL": "hind-left", "HR": "hind-right"}
FEET_COLORS = {"FL": "#1f77b4", "FR": "#ff7f0e", "HL": "#9467bd", "HR": "#8c564b"}
ZOOM = (-0.5, 0.7)  # seconds around the fall shown in the foot-load panel


def main() -> None:
    ans = load_answer()
    fall_s, fall_e = ans["start_ns"], ans["end_ns"]

    with connect() as client:
        seq = client.sequence_handler(SEQUENCE)
        t0 = seq.timestamp_ns_min
        odom = np.array([(m.timestamp_ns, m.data.pose.position.x, m.data.pose.position.y)
                         for m in stream(seq, "/robot/odom")], dtype=np.float64)
        feet = {leg: np.array([(m.timestamp_ns, np.linalg.norm([m.data.force.x, m.data.force.y, m.data.force.z]))
                               for m in stream(seq, f"/contact/{leg}_foot",
                                               fall_s + ZOOM[0] * 1e9, fall_s + ZOOM[1] * 1e9)])
                for leg in FEET}
        imu_t, imu_az = imu_z(seq, fall_s + ZOOM[0] * 1e9, fall_s + ZOOM[1] * 1e9)
        log = mission_log(seq)

    t = (odom[:, 0] - t0) / 1e9
    x, y = odom[:, 1], odom[:, 2]
    dist = float(np.sum(np.hypot(np.diff(x), np.diff(y))))
    i_fall = int(np.searchsorted(odom[:, 0], fall_s))
    air = (odom[:, 0] >= fall_s) & (odom[:, 0] <= fall_e)

    style(plt)
    fig = plt.figure(figsize=(16, 10.5), dpi=150)
    gs = fig.add_gridspec(2, 3, height_ratios=[2.35, 1.0], width_ratios=[1.25, 1.25, 1.0],
                          hspace=0.3, wspace=0.28, left=0.05, right=0.97, top=0.86, bottom=0.07)
    fig.text(0.05, 0.955, "Where spot-07 walked: its patrol spells MOSAICO", fontsize=22, weight="bold", color=INK)
    fig.text(0.05, 0.922,
             f"Odometry of sequence '{SEQUENCE}' streamed from Mosaico  ·  {t[-1]:.1f} s  ·  "
             f"{dist:.1f} m walked  ·  free fall on the letter “A”",
             fontsize=12, color=MUTED)

    # --- trajectory ---------------------------------------------------------------
    ax = fig.add_subplot(gs[0, :])
    pts = np.column_stack([x, y]).reshape(-1, 1, 2)
    lc = LineCollection(np.concatenate([pts[:-1], pts[1:]], axis=1), cmap="viridis", linewidth=3.2,
                        capstyle="round")
    lc.set_array(t[:-1])
    ax.add_collection(lc)
    cb = fig.colorbar(lc, ax=ax, pad=0.01, fraction=0.025)
    cb.set_label("seconds since mission start", color=MUTED)
    ax.plot(x[air], y[air], color=ALERT, lw=7, solid_capstyle="round", zorder=4)

    ax.plot(x[0], y[0], "o", ms=12, color=OK, mec="white", mew=2, zorder=5)
    ax.annotate(f"start  {utc_hms(odom[0, 0])} UTC", (x[0], y[0]), xytext=(12, -16), textcoords="offset points",
                fontsize=10.5, color=OK, weight="bold")
    ax.plot(x[-1], y[-1], "s", ms=11, color=INK, mec="white", mew=2, zorder=5)
    ax.annotate(f"end  {utc_hms(odom[-1, 0])} UTC", (x[-1], y[-1]), xytext=(-10, -22), textcoords="offset points",
                fontsize=10.5, color=INK, weight="bold", ha="right")

    # waypoint groups from the mission log
    for ts, txt in log:
        m = re.search(r"waypoint group (\d+)/(\d+)", txt)
        if m:
            k = int(np.clip(np.searchsorted(odom[:, 0], ts), 0, len(x) - 1))
            ax.plot(x[k], y[k], "o", ms=17, color="white", mec=INK, mew=1.4, zorder=5)
            ax.text(x[k], y[k], m.group(1), ha="center", va="center", fontsize=9, weight="bold", color=INK, zorder=6)

    ax.plot(x[i_fall], y[i_fall], marker="*", ms=30, color=ALERT, mec="white", mew=1.5, zorder=7)
    ax.annotate(f"FREE FALL  t+{(fall_s - t0) / 1e9:.3f} s\n{fall_s} ns\nx = {x[i_fall]:.2f} m, y = {y[i_fall]:.2f} m",
                (x[i_fall], y[i_fall]), xytext=(x[i_fall] + 0.9, y[i_fall] + 1.55), fontsize=11, color=ALERT,
                weight="bold", arrowprops=dict(arrowstyle="->", color=ALERT, lw=1.5),
                bbox=dict(fc="white", ec=ALERT, boxstyle="round,pad=0.4"))

    ax.set_aspect("equal")
    ax.set_xlim(x.min() - 0.8, x.max() + 0.8)
    ax.set_ylim(y.min() - 0.9, y.max() + 2.3)
    ax.set_xlabel("x  [m]  (odometry frame 'world')")
    ax.set_ylabel("y  [m]")
    ax.plot([], [], "o", ms=10, color="white", mec=INK, label="waypoint group reached (mission log)")
    ax.plot([], [], "*", ms=15, color=ALERT, label="free fall (Mosaico query)")
    ax.legend(loc="upper left", frameon=False, fontsize=10, ncol=2)

    # --- foot loads + IMU around the fall ------------------------------------------------
    # Foot loads alone are not a fingerprint of the fall: during normal trotting all four
    # feet are often unloaded for 60-200 ms. Free fall = feet unloaded AND IMU ~ 0 g.
    ax = fig.add_subplot(gs[1, :2])
    clip = 1500.0
    for leg in FEET:
        a = feet[leg]
        ax.plot((a[:, 0] - fall_s) / 1e6, np.minimum(a[:, 1], clip), lw=1.3, color=FEET_COLORS[leg],
                label=FEET_NAMES[leg])
    ax.axvspan(0, (fall_e - fall_s) / 1e6, color=ALERT, alpha=0.18, lw=0)
    land_leg = max(FEET, key=lambda leg: feet[leg][:, 1].max())
    land = feet[land_leg][np.argmax(feet[land_leg][:, 1])]
    ax.annotate(f"landing: {land[1] / 1000:.1f} kN on {FEET_NAMES[land_leg]}\n(clipped at {clip:.0f} N)",
                xy=((land[0] - fall_s) / 1e6, clip), xytext=((land[0] - fall_s) / 1e6 + 200, clip * 1.02),
                fontsize=9.5, color=INK, va="center", arrowprops=dict(arrowstyle="->", color=INK))
    ax.set_ylim(-60, clip * 1.5)
    ax.set_xlim(ZOOM[0] * 1e3, ZOOM[1] * 1e3)
    ax.set_xlabel("milliseconds from free-fall start")
    ax.set_ylabel("foot load |F|  [N]")
    ax.set_title("Around the fall: feet unloaded and IMU ≈ 0 g at the same time", loc="left",
                 fontsize=13, weight="bold")
    ax2 = ax.twinx()
    ax2.plot((imu_t - fall_s) / 1e6, imu_az, color=INK, lw=1.6, ls="--", label="IMU a_z (right axis)")
    ax2.set_ylim(-3, 45)
    ax2.set_ylabel("IMU a_z  [m/s²]")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9.5, ncol=5)

    # --- summary ---------------------------------------------------------------------
    ax = fig.add_subplot(gs[1, 2]); ax.axis("off")
    in_air = [feet[leg][(feet[leg][:, 0] >= fall_s) & (feet[leg][:, 0] <= fall_e), 1].max() for leg in FEET]
    rows = [
        ("Distance walked", f"{dist:.1f} m"),
        ("Duration", f"{t[-1]:.1f} s"),
        ("Mean speed", f"{dist / t[-1]:.2f} m/s"),
        ("Fall position", f"({x[i_fall]:.2f}, {y[i_fall]:.2f}) m"),
        ("Time airborne", f"{ans['duration_ms']:.0f} ms"),
        ("Max foot load in air", f"{max(in_air):.1f} N"),
        ("Landing peak", f"{land[1] / 1000:.1f} kN"),
    ]
    ax.text(0, 1.0, "Patrol summary", fontsize=13, weight="bold", color=INK, va="top", transform=ax.transAxes)
    for j, (k, v) in enumerate(rows):
        yy = 0.84 - j * 0.12
        ax.text(0, yy, k, fontsize=11, color=MUTED, va="top", transform=ax.transAxes)
        ax.text(0.55, yy, v, fontsize=11, color=INK, va="top", weight="bold", transform=ax.transAxes)

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / "where_it_walked.png"
    fig.savefig(out)
    print(f"Saved {out}  ({dist:.1f} m, fall at x={x[i_fall]:.2f}, y={y[i_fall]:.2f})")


if __name__ == "__main__":
    main()
