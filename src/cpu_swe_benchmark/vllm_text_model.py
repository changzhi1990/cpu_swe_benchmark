from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

import requests
from jinja2 import StrictUndefined, Template


ACTION_RE = re.compile(r"```(?:mswea_bash_command|bash)?\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class VLLMTextModelConfig:
    base_url: str
    model_name: str
    api_key: str = "token-abc123"
    max_tokens: int = 512
    temperature: float = 0.0
    repetition_penalty: float | None = 1.05
    timeout_seconds: int = 180
    max_retries: int = 2
    observation_template: str = (
        "{% if output.exception_info %}<exception>{{ output.exception_info }}</exception>\n{% endif %}"
        "<returncode>{{ output.returncode }}</returncode>\n"
        "{% if output.output | length < 8000 %}<output>\n{{ output.output }}</output>"
        "{% else %}<output_head>\n{{ output.output[:4000] }}</output_head>\n"
        "<output_tail>\n{{ output.output[-4000:] }}</output_tail>\n"
        "<warning>Output was truncated.</warning>{% endif %}"
    )
    format_error_template: str = (
        "Format error: expected exactly one fenced command block tagged `mswea_bash_command`, "
        "found {{ actions|length }}. Respond with exactly one command block."
    )


class VLLMTextModel:
    """Minimal text-action model adapter for mini-swe-agent v2.

    The model asks a vLLM OpenAI-compatible chat endpoint for plain text and
    parses exactly one fenced bash command into mini-swe-agent's `extra.actions`.
    """

    def __init__(self, **kwargs):
        self.config = VLLMTextModelConfig(**kwargs)
        self.n_calls = 0
        self.cost = 0.0
        self.call_log: list[dict[str, Any]] = []

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"

    def _payload(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": [{k: v for k, v in msg.items() if k != "extra"} for msg in messages],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self.config.repetition_penalty is not None:
            payload["repetition_penalty"] = self.config.repetition_penalty
        return payload

    def _stream_completion(self, payload: dict[str, Any], headers: dict[str, str]) -> tuple[str, dict[str, Any]]:
        request_payload = {key: value for key, value in payload.items() if not key.startswith("_")}
        response = requests.post(
            self._endpoint(),
            headers=headers,
            json=request_payload,
            timeout=self.config.timeout_seconds,
            stream=True,
        )
        if response.status_code != 200:
            raise RuntimeError(f"vLLM returned HTTP {response.status_code}: {response.text[:500]}")

        content_parts: list[str] = []
        usage: dict[str, Any] = {}
        first_token_timestamp = None
        start = payload["_timestamp_start"]
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data_text = line[len("data: ") :].strip()
            if data_text == "[DONE]":
                break
            chunk = json.loads(data_text)
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices", []):
                fragment = choice.get("delta", {}).get("content")
                if not fragment:
                    continue
                if first_token_timestamp is None:
                    first_token_timestamp = time.time()
                content_parts.append(fragment)
        end = time.time()
        content = "".join(content_parts)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        ttft_seconds = first_token_timestamp - start if first_token_timestamp is not None else None
        tpot_seconds = None
        if first_token_timestamp is not None:
            tpot_seconds = (end - first_token_timestamp) / (completion_tokens - 1) if completion_tokens > 1 else 0.0
        return content, {
            "usage": usage,
            "timestamp_end": end,
            "ttft_seconds": ttft_seconds,
            "tpot_seconds": tpot_seconds,
        }

    def query(self, messages: list[dict[str, Any]], **kwargs) -> dict[str, Any]:
        payload = self._payload(messages)
        if kwargs:
            payload.update(kwargs)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        start = time.time()
        payload["_timestamp_start"] = start
        last_error = ""
        for attempt in range(1, self.config.max_retries + 1):
            try:
                content, data = self._stream_completion(payload, headers)
                actions = self._parse_actions(content)
                usage = data.get("usage", {})
                end = float(data["timestamp_end"])
                self.n_calls += 1
                record = {
                    "call_number": self.n_calls,
                    "timestamp_start": start,
                    "timestamp_end": end,
                    "duration_seconds": end - start,
                    "ttft_seconds": data.get("ttft_seconds"),
                    "tpot_seconds": data.get("tpot_seconds"),
                    "attempt_number": attempt,
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                    "total_tokens": int(usage.get("total_tokens") or 0),
                    "status": "completed",
                }
                self.call_log.append(record)
                return {
                    "role": "assistant",
                    "content": content,
                    "extra": {
                        "actions": actions,
                        "response": {"usage": usage},
                        "cost": 0.0,
                        "timestamp": end,
                    },
                }
            except Exception as exc:
                last_error = str(exc)
                if attempt == self.config.max_retries:
                    end = time.time()
                    self.call_log.append(
                        {
                            "call_number": self.n_calls + 1,
                            "timestamp_start": start,
                            "timestamp_end": end,
                            "duration_seconds": end - start,
                            "attempt_number": attempt,
                            "status": "error",
                            "error": last_error,
                        }
                    )
                    raise
                time.sleep(min(2**attempt, 8))
        raise RuntimeError(last_error)

    def _parse_actions(self, content: str) -> list[dict[str, str]]:
        actions = [match.strip() for match in ACTION_RE.findall(content)]
        if len(actions) != 1:
            self._raise_format_error(actions)
        return [{"command": actions[0]}]

    def _raise_format_error(self, actions: list[str]):
        from minisweagent.exceptions import FormatError

        content = Template(self.config.format_error_template, undefined=StrictUndefined).render(actions=actions)
        raise FormatError({"role": "user", "content": content, "extra": {"interrupt_type": "FormatError"}})

    def format_message(self, **kwargs) -> dict[str, Any]:
        return kwargs

    def format_observation_messages(
        self,
        message: dict[str, Any],
        outputs: list[dict[str, Any]],
        template_vars: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for output in outputs:
            content = Template(self.config.observation_template, undefined=StrictUndefined).render(
                output=output, **(template_vars or {})
            )
            results.append(
                {
                    "role": "user",
                    "content": content,
                    "extra": {
                        "raw_output": output.get("output", ""),
                        "returncode": output.get("returncode"),
                        "timestamp": time.time(),
                        "exception_info": output.get("exception_info", ""),
                    },
                }
            )
        return results

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return asdict(self.config) | {"n_model_calls": self.n_calls, "model_cost": self.cost} | kwargs

    def serialize(self) -> dict[str, Any]:
        return {
            "info": {
                "config": {
                    "model": asdict(self.config),
                    "model_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                }
            }
        }
