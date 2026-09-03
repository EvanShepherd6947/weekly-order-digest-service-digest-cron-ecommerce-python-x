"""Register the public weekly digest route with Infrai cron."""

import os

from infrai import InfraiClient


def schedule_weekly_digest() -> str:
    task_url = os.environ["DIGEST_TASK_URL"]
    data = InfraiClient().create_cron(
        cron_expr="0 9 * * 1",
        task=task_url,
        idempotency_key="weekly-order-digest-v1",
    )
    return str(data["job_id"])


if __name__ == "__main__":
    print(f"Scheduled weekly digest job: {schedule_weekly_digest()}")
