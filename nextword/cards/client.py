import os
import time

from anthropic import Anthropic
from dotenv import load_dotenv


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
