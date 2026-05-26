from types import SimpleNamespace
from nextword.cards.client import (
    submit_batch,
    poll_until_done,
    iter_results,
    generate_one,
    generate_many,
)


class FakeBatches:
    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.retrieve_calls = 0
        self.created_with = None

    def create(self, requests):
        self.created_with = requests
        return SimpleNamespace(id="msgbatch_123")

    def retrieve(self, batch_id):
        self.retrieve_calls += 1
        status = self._statuses.pop(0)
        return SimpleNamespace(processing_status=status)

    def results(self, batch_id):
        return iter([SimpleNamespace(custom_id="req-0")])


class FakeMessages:
    def __init__(self, statuses):
        self.batches = FakeBatches(statuses)
        self.created_with = None

    def create(self, **params):
        self.created_with = params
        return SimpleNamespace(content=["msg"])


def _client(statuses=("ended",)):
    return SimpleNamespace(messages=FakeMessages(statuses))


def test_submit_batch_returns_id():
    client = _client()
    bid = submit_batch(client, [{"custom_id": "req-0", "params": {}}])
    assert bid == "msgbatch_123"
    assert client.messages.batches.created_with == [{"custom_id": "req-0", "params": {}}]


def test_poll_until_done_loops_until_ended():
    client = _client(statuses=["in_progress", "in_progress", "ended"])
    calls = []
    poll_until_done(client, "msgbatch_123", interval=5, sleep=calls.append)
    assert client.messages.batches.retrieve_calls == 3
    assert calls == [5, 5]  # slept twice, not after the final "ended"


def test_iter_results_delegates():
    client = _client()
    out = list(iter_results(client, "msgbatch_123"))
    assert out[0].custom_id == "req-0"


def test_generate_one_calls_messages_create_with_params():
    client = _client()
    request = {"custom_id": "req-0", "params": {"model": "m", "max_tokens": 10}}
    msg = generate_one(client, request)
    assert msg.content == ["msg"]
    assert client.messages.created_with == {"model": "m", "max_tokens": 10}


def test_generate_many_preserves_order_and_captures_errors():
    class _Messages:
        def create(self, **params):
            content = params["messages"][0]["content"]
            if content == "boom":
                raise RuntimeError("fail")
            return SimpleNamespace(content=content)

    client = SimpleNamespace(messages=_Messages())
    requests = [
        {"custom_id": "req-0", "params": {"messages": [{"role": "user", "content": "a"}]}},
        {"custom_id": "req-1", "params": {"messages": [{"role": "user", "content": "boom"}]}},
        {"custom_id": "req-2", "params": {"messages": [{"role": "user", "content": "c"}]}},
    ]

    results = generate_many(client, requests, max_workers=3)

    assert [status for status, _ in results] == ["ok", "error", "ok"]
    assert results[0][1].content == "a"
    assert isinstance(results[1][1], RuntimeError)
    assert results[2][1].content == "c"
