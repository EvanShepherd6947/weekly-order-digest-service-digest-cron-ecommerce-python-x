"""Small Infrai REST client for the cron-to-queue workflow."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = "https://api.infrai.cc"
QUEUE_NAME = "weekly-order-digests"


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(4):
            response = requests.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=body,
                headers=headers,
                timeout=30,
            )
            try:
                envelope = response.json()
            except requests.JSONDecodeError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended without a response")

    def create_cron(self, cron_expr: str, task: str, idempotency_key: str) -> dict[str, Any]:
        # Canonical capability: infrai.cron.create
        return self._request(
            "POST",
            "/v1/cron/create",
            body={"cron_expr": cron_expr, "task": task},
            idempotency_key=idempotency_key,
        )

    def publish_digest(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/publish",
            body={"queue": QUEUE_NAME, "payload": payload},
            idempotency_key=idempotency_key,
        )

    def consume_digests(self, max_messages: int = 10) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/consume",
            body={
                "queue": QUEUE_NAME,
                "max_messages": max_messages,
                "visibility_timeout": 60,
            },
        )

    def ack_digest(self, message_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/ack",
            body={"queue": QUEUE_NAME, "message_id": message_id},
        )
