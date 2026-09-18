"""
VĀSTU Mobile Capture: Write-Ahead Session Journal
Guarantees session recoverability by writing append-only checkpoint events to disk.
"""

import os
import json
import time
from typing import Dict, Any, List

class CaptureSessionJournal:
    JOURNAL_FILENAME = "session_journal.jsonl"

    def __init__(self, session_dir: str):
        self.session_dir = session_dir
        self.journal_path = os.path.join(session_dir, self.JOURNAL_FILENAME)
        os.makedirs(session_dir, exist_ok=True)

    def log_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Appends a structured JSON event and forces immediate disk sync.
        """
        record = {
            "event": event_type,
            "timestamp_ns": time.time_ns(),
            "payload": payload
        }
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def read_events(self) -> List[Dict[str, Any]]:
        """
        Reads all journal entries in chronological order.
        """
        if not os.path.exists(self.journal_path):
            return []

        events = []
        with open(self.journal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return events
