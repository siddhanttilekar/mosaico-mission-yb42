"""Shared helpers for the YB-42 scripts: Mosaico access, the step-2 answer, styling."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from mosaicolabs import MosaicoClient

HOST, PORT = "localhost", 6726
SEQUENCE = "spot_yb42"
ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Palette used by every figure
INK = "#1f2430"
MUTED = "#6b7280"
GRID = "#e5e7eb"
ALERT = "#d62728"   # free fall
OK = "#2ca02c"      # start


def connect():
    return MosaicoClient.connect(host=HOST, port=PORT)


def load_answer() -> dict:
    """The free-fall window found by scripts/02_find_freefall.py."""
    path = RESULTS / "answer.json"
    if not path.exists():
        raise SystemExit("results/answer.json missing - run scripts/02_find_freefall.py first.")
    return json.loads(path.read_text())


def stream(seq, topic: str, start_ns: int | None = None, end_ns: int | None = None):
    """Yield messages of one topic, optionally sliced server-side to [start_ns, end_ns]."""
    kwargs = {}
    if start_ns is not None:
        kwargs["start_timestamp_ns"] = int(start_ns)
    if end_ns is not None:
        kwargs["end_timestamp_ns"] = int(end_ns)
    yield from seq.get_topic_handler(topic).get_data_streamer(**kwargs)


def imu_z(seq, start_ns=None, end_ns=None):
    rows = [(m.timestamp_ns, m.data.acceleration.z) for m in stream(seq, "/imu/body", start_ns, end_ns)]
    a = np.array(rows, dtype=np.float64)
    return a[:, 0].astype(np.int64), a[:, 1]


def mission_log(seq):
    """[(timestamp_ns, text), ...] from /robot/status."""
    return [(m.timestamp_ns, m.data.data) for m in stream(seq, "/robot/status")]


def utc_hms(ns: int) -> str:
    sec, frac = divmod(int(ns), 1_000_000_000)
    return datetime.fromtimestamp(sec, timezone.utc).strftime("%H:%M:%S") + f".{frac // 1_000_000:03d}"


def style(plt):
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    })
