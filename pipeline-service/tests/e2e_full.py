"""Print full YAML + events for the latest run."""

import sys
import time
from pathlib import Path

import httpx


def main() -> int:
    sample = Path("C:/WorkSpace/novel2script/sample-novel.txt")
    content = sample.read_bytes()
    print(f"Loaded sample-novel.txt: {len(content)} bytes\n")

    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "http://localhost:8000/pipeline",
            files={"file": ("sample-novel.txt", content, "text/plain")},
        )
        run_id = r.json()["run_id"]
        print(f"Submitted run_id: {run_id}")

        # Wait for done
        for i in range(60):
            time.sleep(2)
            s = httpx.get(
                f"http://localhost:8000/pipeline/{run_id}/status", timeout=5.0,
            ).json()
            if s.get("stage") in ("done", "failed:orchestrator") or (
                s.get("stage", "").startswith("failed")
            ):
                break

        # Print full YAML
        r = httpx.get(f"http://localhost:8000/pipeline/{run_id}/result", timeout=5.0)
        if r.status_code == 200:
            yaml_str = r.json()["yaml"]
            print(f"\n{'='*70}")
            print(f"FULL YAML ({len(yaml_str)} chars)")
            print(f"{'='*70}")
            print(yaml_str)
            print(f"{'='*70}\n")

        # Print events
        r = httpx.get(
            f"http://localhost:8000/pipeline/{run_id}/events?count=100", timeout=5.0,
        )
        events = r.json().get("events", [])
        print(f"\n{'='*70}")
        print(f"EVENT AUDIT TRAIL ({len(events)} events)")
        print(f"{'='*70}")
        for e in events:
            print(f"  {e['type']:35s} from {e.get('source', '?'):20s} corr={e.get('correlation_id', '') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
