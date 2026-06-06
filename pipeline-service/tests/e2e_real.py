"""End-to-end smoke test: submit sample novel, poll for completion,
verify YAML result + Redis state. Runs against the locally-running
4 services + Redis."""

import sys
import time
from pathlib import Path

import httpx


def main() -> int:
    sample = Path(__file__).parent.parent / "sample-novel.txt"
    if not sample.exists():
        # Try relative to repo root
        sample = Path("C:/WorkSpace/novel2script/sample-novel.txt")
    if not sample.exists():
        print(f"ERROR: sample-novel.txt not found at {sample}")
        return 1
    content = sample.read_bytes()
    print(f"Loaded sample-novel.txt: {len(content)} bytes")

    # Submit
    print("\n=== Submitting pipeline ===")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "http://localhost:8000/pipeline",
            files={"file": ("sample-novel.txt", content, "text/plain")},
        )
        print(f"Submit status: {r.status_code}")
        print(f"Submit body: {r.json()}")
        if r.status_code != 200:
            return 1
        run_id = r.json()["run_id"]

    # Poll
    print("\n=== Polling status ===")
    last_stage = None
    for i in range(60):
        time.sleep(3)
        try:
            s = httpx.get(
                f"http://localhost:8000/pipeline/{run_id}/status", timeout=5.0,
            ).json()
        except Exception as e:
            print(f"  poll error: {e}")
            continue
        stage = s.get("stage", "?")
        progress = s.get("progress", "?")
        if stage != last_stage:
            print(f"  poll #{i+1}: stage={stage!r} progress={progress!r}")
            last_stage = stage
        if stage == "done":
            break
        if stage and stage.startswith("failed"):
            print(f"  FAILED: {s.get('error')}")
            break

    # Result
    print("\n=== Fetching result ===")
    r = httpx.get(f"http://localhost:8000/pipeline/{run_id}/result", timeout=5.0)
    print(f"Result status: {r.status_code}")
    if r.status_code == 200:
        yaml_str = r.json()["yaml"]
        print(f"YAML length: {len(yaml_str)} chars")
        print("\n--- YAML (first 1000 chars) ---")
        print(yaml_str[:1000])
        print("--- end preview ---")

    # Events
    print("\n=== Event audit trail ===")
    r = httpx.get(
        f"http://localhost:8000/pipeline/{run_id}/events?count=50", timeout=5.0,
    )
    events = r.json().get("events", [])
    print(f"Total events: {len(events)}")
    for e in events[:15]:
        print(f"  {e['type']:35s} from {e.get('source', '?'):20s}")
    if len(events) > 15:
        print(f"  ... and {len(events) - 15} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())
