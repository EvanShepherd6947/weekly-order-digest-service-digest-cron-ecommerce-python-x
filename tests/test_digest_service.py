from digest_service import DigestRequest, build_customer_digests


def test_digest_includes_only_paid_orders_with_receipts() -> None:
    request = DigestRequest.model_validate(
        {
            "week": "2026-W34",
            "orders": [
                {
                    "order_id": "ord_paid",
                    "customer_email": "maker@example.com",
                    "checkout": "paid",
                    "fulfillment": "shipped",
                    "receipt_sent": True,
                },
                {
                    "order_id": "ord_pending",
                    "customer_email": "maker@example.com",
                    "checkout": "pending",
                    "fulfillment": "packing",
                    "receipt_sent": False,
                },
            ],
        }
    )

    digests = build_customer_digests(request)

    assert [digest.model_dump() for digest in digests] == [
        {
            "customer_email": "maker@example.com",
            "week": "2026-W34",
            "items": [{"order_id": "ord_paid", "update": "shipped"}],
        }
    ]
