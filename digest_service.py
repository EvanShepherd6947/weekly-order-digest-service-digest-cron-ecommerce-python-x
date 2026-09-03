"""HTTP service that turns weekly order activity into queued customer digests."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from infrai import InfraiClient, InfraiError


class OrderUpdate(BaseModel):
    order_id: str
    customer_email: str
    checkout: Literal["paid", "pending", "cancelled"]
    fulfillment: Literal["packing", "shipped", "delivered"]
    receipt_sent: bool


class DigestRequest(BaseModel):
    week: str = Field(pattern=r"^\d{4}-W\d{2}$")
    orders: list[OrderUpdate]


class DigestItem(BaseModel):
    order_id: str
    update: str


class CustomerDigest(BaseModel):
    customer_email: str
    week: str
    items: list[DigestItem]


class QueueResult(BaseModel):
    queued: int


class AcceptedUpdate(BaseModel):
    accepted: bool


order_updates: list[OrderUpdate] = []


def build_customer_digests(request: DigestRequest) -> list[CustomerDigest]:
    """Include paid orders with a receipt and group updates by customer."""
    grouped: dict[str, list[DigestItem]] = {}
    for order in request.orders:
        if order.checkout != "paid" or not order.receipt_sent:
            continue
        grouped.setdefault(order.customer_email, []).append(
            DigestItem(order_id=order.order_id, update=order.fulfillment)
        )
    return [
        CustomerDigest(customer_email=email, week=request.week, items=items)
        for email, items in sorted(grouped.items())
    ]


app = FastAPI(title="Weekly order digest")


@app.post("/orders/updates", response_model=AcceptedUpdate)
def record_order_update(update: OrderUpdate) -> AcceptedUpdate:
    order_updates.append(update)
    return AcceptedUpdate(accepted=True)


@app.post("/jobs/weekly-digest", response_model=QueueResult)
def queue_weekly_digest() -> QueueResult:
    client = InfraiClient()
    year, week_number, _ = date.today().isocalendar()
    request = DigestRequest(week=f"{year}-W{week_number:02d}", orders=order_updates)
    digests = build_customer_digests(request)
    try:
        for digest in digests:
            stable_key = hashlib.sha256(
                f"{digest.week}:{digest.customer_email}".encode()
            ).hexdigest()
            client.publish_digest(digest.model_dump(), f"digest-{stable_key}")
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc
    order_updates.clear()
    return QueueResult(queued=len(digests))
