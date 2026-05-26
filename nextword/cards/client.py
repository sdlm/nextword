import os
import time
from concurrent.futures import ThreadPoolExecutor

from anthropic import Anthropic
from dotenv import load_dotenv

from nextword.cards.schema import CONCURRENCY


def make_client() -> Anthropic:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set (add it to .env)")
    return Anthropic()


def submit_batch(client, requests: list[dict]) -> str:
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def poll_until_done(client, batch_id: str, interval: int = 30, sleep=time.sleep):
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        sleep(interval)


def iter_results(client, batch_id: str):
    return client.messages.batches.results(batch_id)


def generate_one(client, request: dict):
    return client.messages.create(**request["params"])


def generate_many(client, requests: list[dict], *, max_workers: int = CONCURRENCY):
    # Run all requests in parallel; return ("ok", message) or ("error", exc)
    # per request, in the same order as the input list.
    results: list = [None] * len(requests)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_one, client, req): i
            for i, req in enumerate(requests)
        }
        for future, i in futures.items():
            try:
                results[i] = ("ok", future.result())
            except Exception as exc:  # noqa: BLE001 - report per-request, keep others
                results[i] = ("error", exc)
    return results
