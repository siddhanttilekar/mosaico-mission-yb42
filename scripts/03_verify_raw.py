"""
Step 3 - Independently verify Mosaico's answer against the raw MCAP file.

Reads /imu/body straight from spot_yb42.mcap (no Mosaico involved), finds the
same free-fall window, and checks that it matches results/answer.json.
It also sweeps the "almost zero" threshold to show the start time does not
hinge on one hand-picked number.

Usage:  python scripts/03_verify_raw.py
Output: results/threshold_sweep.csv and a PASS/FAIL line.
"""

import json
from pathlib import Path

import numpy as np
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

ROOT = Path(__file__).resolve().parent.parent
MCAP = ROOT / "Hackathon-challenge" / "spot_yb42.mcap"
RESULTS = ROOT / "results"
GAP_NS = 100_000_000  # same 100 ms clustering gap as the Mosaico query


def load_imu():
    """Return (log_time_ns, header_stamp_ns, accel_z) arrays for /imu/body."""
    log_t, hdr_t, az = [], [], []
    with open(MCAP, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for _, _, msg, ros in reader.iter_decoded_messages(topics=["/imu/body"]):
            log_t.append(msg.log_time)
            hdr_t.append(ros.header.stamp.sec * 1_000_000_000 + ros.header.stamp.nanosec)
            az.append(ros.linear_acceleration.z)
    return np.array(log_t, dtype=np.int64), np.array(hdr_t, dtype=np.int64), np.array(az)


def windows(t, mask):
    """Group matching timestamps into clusters separated by more than GAP_NS."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    out, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if t[i] - t[prev] > GAP_NS:
            out.append((t[start], t[prev]))
            start = i
        prev = i
    out.append((t[start], t[prev]))
    return out


def main() -> None:
    log_t, hdr_t, az = load_imu()
    t0 = log_t[0]
    print(f"Raw IMU samples: {len(az)} at {len(az) / ((log_t[-1] - t0) / 1e9):.0f} Hz")

    # 1) Same filter as the Mosaico query
    w = windows(log_t, np.abs(az) <= 1.0)
    start, end = w[0]
    i0 = int(np.searchsorted(log_t, start))
    print(f"Raw free-fall window : {start} -> {end} ({(end - start) / 1e6:.0f} ms, {len(w)} window(s))")
    print(f"  sample before : t+{(log_t[i0-1] - t0) / 1e9:.3f}s  az = {az[i0-1]:+.3f} m/s^2")
    print(f"  first in fall : t+{(log_t[i0] - t0) / 1e9:.3f}s  az = {az[i0]:+.3f} m/s^2")
    print(f"  sensor header stamp of that sample: {hdr_t[i0]} (log time is what Mosaico indexes)")

    # 2) Threshold sensitivity sweep
    rows = ["threshold_m_s2,windows,first_start_ns,first_start_s,first_duration_ms"]
    print("\n|az| <= thr   windows  first start (s)  duration (ms)")
    for thr in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        ws = windows(log_t, np.abs(az) <= thr)
        s, e = ws[0]
        print(f"   {thr:4.2f}      {len(ws):5d}     {(s - t0) / 1e9:8.3f}      {(e - s) / 1e6:7.0f}")
        rows.append(f"{thr},{len(ws)},{s},{(s - t0) / 1e9:.3f},{(e - s) / 1e6:.0f}")
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "threshold_sweep.csv").write_text("\n".join(rows) + "\n")

    # 3) Cross-check with Mosaico's answer
    ans_file = RESULTS / "answer.json"
    if ans_file.exists():
        ans = json.loads(ans_file.read_text())
        ok = ans["start_ns"] == int(start) and ans["end_ns"] == int(end)
        print(f"\nMosaico start_ns {ans['start_ns']} vs raw {start}: {'PASS' if ok else 'FAIL'}")
    else:
        print("\n(run 02_find_freefall.py first to cross-check against Mosaico)")


if __name__ == "__main__":
    main()
