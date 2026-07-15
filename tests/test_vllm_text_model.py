import json

from cpu_swe_benchmark import vllm_text_model
from cpu_swe_benchmark.vllm_text_model import VLLMTextModel


class FakeStreamResponse:
    status_code = 200
    text = ""

    def iter_lines(self, decode_unicode=False):
        chunks = [
            {"choices": [{"delta": {"content": "```mswea_bash_command\n"}}]},
            {"choices": [{"delta": {"content": "echo ok"}}]},
            {"choices": [{"delta": {"content": "\n```"}}]},
            {
                "choices": [],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        ]
        for chunk in chunks:
            line = f"data: {json.dumps(chunk)}"
            yield line if decode_unicode else line.encode()
        yield "data: [DONE]" if decode_unicode else b"data: [DONE]"


def test_vllm_text_model_records_streaming_ttft_and_tpot(monkeypatch):
    times = iter([100.0, 100.25, 100.75])
    monkeypatch.setattr(vllm_text_model.time, "time", lambda: next(times))

    def fake_post(url, *, headers, json, timeout, stream):
        assert stream is True
        assert json["stream"] is True
        assert json["stream_options"]["include_usage"] is True
        return FakeStreamResponse()

    monkeypatch.setattr(vllm_text_model.requests, "post", fake_post)
    model = VLLMTextModel(
        base_url="http://localhost:8000/v1",
        model_name="qwen2.5-coder-32b",
        api_key="token-abc123",
    )

    response = model.query([{"role": "user", "content": "run command"}])

    assert response["content"] == "```mswea_bash_command\necho ok\n```"
    assert response["extra"]["actions"] == [{"command": "echo ok"}]
    assert model.call_log[0]["ttft_seconds"] == 0.25
    assert model.call_log[0]["tpot_seconds"] == 0.125
    assert model.call_log[0]["prompt_tokens"] == 10
    assert model.call_log[0]["completion_tokens"] == 5
    assert model.call_log[0]["total_tokens"] == 15


def test_vllm_text_model_defaults_to_compact_completion_budget():
    model = VLLMTextModel(
        base_url="http://localhost:8000/v1",
        model_name="qwen2.5-coder-32b",
        api_key="token-abc123",
    )

    assert model.config.max_tokens == 512
