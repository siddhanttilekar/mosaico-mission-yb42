"""
Step 2 - Find the free-fall window of spot-07 with a single Mosaico query.

Physics: an accelerometer measures *specific force* (acceleration minus
gravity). Standing or walking, the IMU's vertical axis reads about +9.8 m/s^2.
In free fall the sensor falls together with the body, so it reads about 0.
We therefore ask Mosaico for the IMU samples where acceleration.z is within
+/-1 m/s^2 of zero (about 0.1 g) and let the server tell us *when* that holds.

The query is evaluated server side by mosaicod:
  1. client.query(...)  -> which topic matches (sequence + topic + IMU filter)
  2. .clusterize(...)   -> the exact [start_ns, end_ns] windows of the matches
                           (mosaicod action `topic_filter_clusterize`)

Usage:  python scripts/02_find_freefall.py
Output: results/answer.json and the answer printed to the terminal.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from mosaicolabs import IMU, MosaicoClient, QueryOntologyCatalog, QuerySequence, QueryTopic

HOST, PORT = "localhost", 6726
SEQUENCE = "spot_yb42"
IMU_TOPIC = "/imu/body"
Z_BAND = [-1.0, 1.0]            # m/s^2, "almost no vertical acceleration" (~0.1 g)
CLUSTER_GAP_NS = 100_000_000    # 100 ms: matches closer than this are one event

RESULTS = Path(__file__).resolve().parent.parent / "results"


def utc(ns: int) -> str:
    """Nanosecond epoch -> ISO-8601 UTC string, keeping full ns precision."""
    sec, frac = divmod(ns, 1_000_000_000)
    return datetime.fromtimestamp(sec, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{frac:09d}Z"


def main() -> None:
    with MosaicoClient.connect(host=HOST, port=PORT) as client:
        seq = client.sequence_handler(SEQUENCE)
        t0 = seq.timestamp_ns_min

        # ---- THE query -----------------------------------------------------
        response = client.query(
            QuerySequence().with_name(SEQUENCE),
            QueryTopic().with_name(IMU_TOPIC),
            QueryOntologyCatalog(IMU.Q.acceleration.z.between(Z_BAND)),
        )
        # --------------------------------------------------------------------

        if not response:
            raise SystemExit("No IMU samples matched - nothing to report.")

        topic = response[0].topics[0]
        windows = topic.clusterize(clustering_dt_ns=CLUSTER_GAP_NS)

    print(f"Matched topic: {topic.locator}  (ontology: {topic.ontology_tag})")
    print(f"Free-fall windows found: {len(windows)}")
    for w in windows:
        s, e = w.timerange.start, w.timerange.end
        print(f"  #{w.id}: {s} -> {e}  | t+{(s - t0) / 1e9:.3f}s, lasts {(e - s) / 1e6:.0f} ms")

    first = windows[0].timerange
    answer = {
        "sequence": SEQUENCE,
        "topic": topic.locator,
        "filter": f"IMU.acceleration.z between {Z_BAND} m/s^2",
        "start_ns": first.start,
        "end_ns": first.end,
        "start_utc": utc(first.start),
        "end_utc": utc(first.end),
        "seconds_into_mission": round((first.start - t0) / 1e9, 3),
        "duration_ms": round((first.end - first.start) / 1e6, 3),
        "windows_found": len(windows),
        # The exact request mosaicod receives for the time windows, for anyone
        # who wants to reproduce it without the Python SDK.
        "mosaicod_request": {
            "action": "topic_filter_clusterize",
            "locator": topic.locator,
            "clustering_dt_ns": CLUSTER_GAP_NS,
            "ontology": {"IMU.acceleration.z": {"$between": Z_BAND}},
        },
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "answer.json").write_text(json.dumps(answer, indent=2) + "\n")

    print("\n================  ANSWER  ================")
    print(f"Free fall starts at : {answer['start_ns']} ns")
    print(f"                    = {answer['start_utc']}")
    print(f"                    = t+{answer['seconds_into_mission']} s into the mission")
    print(f"Duration            : {answer['duration_ms']} ms")
    print("==========================================")
    print(f"Saved to {RESULTS / 'answer.json'}")


if __name__ == "__main__":
    main()
