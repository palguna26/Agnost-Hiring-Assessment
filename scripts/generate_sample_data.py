from __future__ import annotations

import argparse
import json
from pathlib import Path


SAMPLE_CONVERSATIONS: list[dict[str, object]] = [
    {
        "session_id": "sess_refund_001",
        "user_id": "user_001",
        "timestamp": "2026-05-24T09:00:00Z",
        "source": "agnost_sdk",
        "messages": [
            {"role": "user", "content": "I still have not received my refund after two weeks."},
            {"role": "assistant", "content": "I can check the status for you."},
        ],
        "metadata": {"product": "billing", "channel": "email", "priority": "high"},
    },
    {
        "session_id": "sess_refund_002",
        "user_id": "user_002",
        "timestamp": "2026-05-24T09:20:00Z",
        "source": "agnost_sdk",
        "messages": [
            {"role": "user", "content": "The refund flow is broken and I keep getting an error."},
            {"role": "assistant", "content": "Thanks for reporting this. We will investigate."},
        ],
        "metadata": {"product": "billing", "channel": "chat", "priority": "high"},
    },
    {
        "session_id": "sess_feature_001",
        "user_id": "user_003",
        "timestamp": "2026-05-24T10:05:00Z",
        "source": "agnost_sdk",
        "messages": [
            {"role": "user", "content": "Could you add a dark mode toggle to the dashboard?"},
            {"role": "assistant", "content": "That is a helpful request and I will share it with the team."},
        ],
        "metadata": {"product": "dashboard", "channel": "in-app", "priority": "medium"},
    },
]


def write_sample_data(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in SAMPLE_CONVERSATIONS:
            handle.write(json.dumps(record, ensure_ascii=True))
            handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample conversation JSONL data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/sample_conversations.jsonl"),
        help="Path to the JSONL file to write.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_sample_data(args.output)
    print(f"Wrote {len(SAMPLE_CONVERSATIONS)} sample conversations to {args.output}")


if __name__ == "__main__":
    main()
