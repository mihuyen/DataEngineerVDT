from __future__ import annotations

import os

from kafka import KafkaAdminClient, KafkaConsumer
from kafka.structs import TopicPartition

# Must match sql/streaming/realtime_vwap_kafka_engine.sql's kafka_topic_list /
# kafka_group_name -- this is the one real consumer group in the stack
# (ClickHouse's own Kafka table engine consumes it directly; nothing else
# does).
DEFAULT_TOPIC = "dnse-trades-raw"
DEFAULT_GROUP_ID = "clickhouse-realtime-vwap"


def get_consumer_group_lag(
    bootstrap_servers: str | None = None,
    topic: str = DEFAULT_TOPIC,
    group_id: str = DEFAULT_GROUP_ID,
) -> list[dict]:
    """Real per-partition lag for `group_id`, computed from broker offsets.

    lag = high-water-mark offset (end_offsets) - last committed offset
    (list_consumer_group_offsets), both read straight from the Kafka broker.
    Returns [] if the topic doesn't exist yet or the broker is unreachable --
    callers should treat that the same as "no lag data available", not as a
    sentinel zero (a sentinel would be indistinguishable from "actually caught
    up").
    """
    servers = (bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")).split(",")

    try:
        consumer = KafkaConsumer(bootstrap_servers=servers, group_id=None, consumer_timeout_ms=5000)
        try:
            partitions = consumer.partitions_for_topic(topic)
            if not partitions:
                return []
            topic_partitions = [TopicPartition(topic, partition) for partition in sorted(partitions)]
            end_offsets = consumer.end_offsets(topic_partitions)
        finally:
            consumer.close()

        admin = KafkaAdminClient(bootstrap_servers=servers)
        try:
            committed = admin.list_group_offsets(group_id).get(group_id, {})
        finally:
            admin.close()
    except Exception:
        return []

    result = []
    for tp in topic_partitions:
        end_offset = end_offsets.get(tp, 0)
        meta = committed.get(tp)
        current_offset = meta.offset if meta and meta.offset >= 0 else 0
        result.append(
            {
                "partition": tp.partition,
                "currentOffset": current_offset,
                "endOffset": end_offset,
                "lag": max(end_offset - current_offset, 0),
            }
        )
    return result
