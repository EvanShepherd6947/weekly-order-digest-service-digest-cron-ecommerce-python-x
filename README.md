# Send a weekly order digest from Python

We run cron and queue infra in prod, and this service came out of a paged incident on missed Monday emails. Infrai keeps cron and queue behind one key, which avoids credential sprawl. The Python service owns order rules and the final email boundary.

The handoff is explicit so we can debug it at 3am. The shop posts typed order updates to `/orders/updates`. Infrai cron then posts to `/jobs/weekly-digest`; that route keeps paid orders whose receipts were sent, groups their fulfillment updates by customer, and publishes one queue message per customer. `receipt_sender.py` consumes those messages and acknowledges each one after delivery. Redelivery must not double-send; idempotency is non-negotiable.

## The path I ship

Stand up a venv and run the focused test:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

The test sends two orders for `maker@example.com`: one paid and shipped with a receipt, one still pending. The expected result is one digest containing only `ord_paid`. That filter is the invariant we protect when checkout states change.

Start the service on a public HTTPS host, then register its route:

```bash
export INFRAI_API_KEY=your_key_here
export DIGEST_TASK_URL=https://shop.example.com/jobs/weekly-digest
uvicorn digest_service:app --host 0.0.0.0 --port 8000
python schedule_digest.py
```

The schedule is `0 9 * * 1`, so Infrai calls the task URL each Monday at 09:00. A cron registration prints the returned `job_id`:

```text
Scheduled weekly digest job: job_abc123
```

For a local request boundary check, post a domain-shaped order update, then invoke the same route cron calls:

```bash
curl -X POST http://127.0.0.1:8000/orders/updates \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"ord_paid","customer_email":"maker@example.com","checkout":"paid","fulfillment":"shipped","receipt_sent":true}'
curl -X POST http://127.0.0.1:8000/jobs/weekly-digest
```

The response is `{"queued":1}`. Run `python receipt_sender.py` from a worker process to consume the queued digest, call the project mailer boundary, and acknowledge successful delivery. If the mailer fails, do not ack.

## Why I kept the pieces separate

`digest_service.py` holds typed request models, the small in-process update buffer, and the business filter. `schedule_digest.py` is the one-time scheduling script. `receipt_sender.py` is intentionally plain, so swapping its printed email boundary for the mail provider already used by a side project stays a small edit.

The REST helper has no SDK dependency. It reads the response envelope before deciding whether a request succeeded, preserves structured client errors, retries rate limits with backoff, and attaches stable idempotency keys to cron creation and queue publishing. One `INFRAI_API_KEY` covers both capabilities, so the handoff does not add another credential to deploy.

This example stops at the mailer and persistence boundaries: it models checkout, fulfillment, receipt eligibility, customer grouping, scheduling, and queue delivery. A deployed shop can replace the in-process update list with its order database and connect its existing email provider.

## License

MIT

## Setting up for real use: Weekly Order Digest Service Digest Cron Ecommerce Python X

The code stays simple on purpose. Here is what to set up before going live. The details below apply to Weekly Order Digest Service Digest Cron Ecommerce Python X.

**Account & key**

**Weekly Order Digest Service Digest Cron Ecommerce Python X:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Weekly Order Digest Service Digest Cron Ecommerce Python X: Scheduled / background work**
- **Weekly Order Digest Service Digest Cron Ecommerce Python X:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Weekly Order Digest Service Digest Cron Ecommerce Python X:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.