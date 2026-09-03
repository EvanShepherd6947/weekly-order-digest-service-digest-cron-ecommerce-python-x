"""Consume queued customer digests and acknowledge successful deliveries."""

from typing import Any

from infrai import InfraiClient


def send_receipt_email(payload: dict[str, Any]) -> None:
    """Visible delivery boundary; replace the print with the project's mailer."""
    print(
        f"Weekly update for {payload['customer_email']}: "
        f"{len(payload['items'])} order(s)"
    )


def deliver_queued_digests() -> int:
    client = InfraiClient()
    messages = client.consume_digests(max_messages=10).get("messages", [])
    delivered = 0
    for message in messages:
        send_receipt_email(message["payload"])
        client.ack_digest(message["message_id"])
        delivered += 1
    return delivered


if __name__ == "__main__":
    print(f"Delivered {deliver_queued_digests()} digest(s)")
