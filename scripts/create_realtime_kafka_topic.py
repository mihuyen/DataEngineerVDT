from __future__ import annotations

import argparse
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Kafka topic for realtime trade ticks.")
    parser.add_argument("--topic", default="dnse-trades-raw")
    parser.add_argument("--partitions", type=int, default=3)
    parser.add_argument("--replication-factor", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    command = [
        "docker",
        "exec",
        "stock-kafka",
        "kafka-topics",
        "--bootstrap-server",
        "localhost:9092",
        "--create",
        "--if-not-exists",
        "--topic",
        args.topic,
        "--partitions",
        str(args.partitions),
        "--replication-factor",
        str(args.replication_factor),
    ]
    subprocess.run(command, check=True)
    print(f"Kafka topic ready: {args.topic}")


if __name__ == "__main__":
    main()
