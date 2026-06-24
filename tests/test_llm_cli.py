import json

import pytest
from pydantic import BaseModel

import app.llm_cli as cli


class Toy(BaseModel):
    name: str
    score: int


def test_messages_to_prompt():
    s, h = cli._messages_to_prompt([("system", "S1"), ("human", "H1"), ("system", "S2")])
    assert "S1" in s and "S2" in s
    assert h == "H1"


def test_extract_json_plain():
    assert json.loads(cli._extract_json('{"a": 1}'))["a"] == 1


def test_extract_json_fenced():
    raw = "前言\n```json\n{\"a\": 2}\n```\n後語"
    assert json.loads(cli._extract_json(raw))["a"] == 2


def test_extract_json_embedded():
    raw = "這是結果：{\"a\": 3} 謝謝"
    assert json.loads(cli._extract_json(raw))["a"] == 3


def test_extract_json_nested_object():
    # 巢狀物件：舊的「第一個 { 到最後一個 }」在有後綴雜訊時會壞，平衡掃描要正確
    raw = '前言 {"outer": {"inner": [1, 2]}, "name": "王"} 後綴'
    obj = json.loads(cli._extract_json(raw))
    assert obj["outer"]["inner"] == [1, 2] and obj["name"] == "王"


def test_extract_json_stops_at_first_complete_object():
    raw = '{"a": 1} 然後又冒出一段 {"b": 2}'
    assert json.loads(cli._extract_json(raw)) == {"a": 1}


def test_extract_json_brace_inside_string():
    raw = '{"note": "包含 } 與 { 大括號", "score": 7}'
    assert json.loads(cli._extract_json(raw))["score"] == 7


def test_claude_structured_repairs_validation_error(monkeypatch):
    # 驗證失敗時，重試提示要帶欄位級錯誤（提到缺少的 score），而非通用嘮叨
    prompts = []
    calls = {"n": 0}

    def runner(prompt, model):
        prompts.append(prompt)
        calls["n"] += 1
        return '{"name": "x"}' if calls["n"] == 1 else '{"name": "x", "score": 9}'

    monkeypatch.setattr(cli, "_run_claude", runner)
    out = cli.ClaudeCLIChat("haiku").with_structured_output(Toy).invoke([("human", "h")])
    assert out.score == 9 and calls["n"] == 2
    assert "score" in prompts[1]


def test_claude_structured_parses(monkeypatch):
    monkeypatch.setattr(cli, "_run_claude", lambda prompt, model: '{"name": "王", "score": 88}')
    llm = cli.ClaudeCLIChat("opus")
    out = llm.with_structured_output(Toy).invoke([("system", "s"), ("human", "h")])
    assert isinstance(out, Toy)
    assert out.name == "王" and out.score == 88


def test_claude_structured_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def runner(prompt, model):
        calls["n"] += 1
        return "亂碼非 JSON" if calls["n"] == 1 else '{"name": "x", "score": 1}'

    monkeypatch.setattr(cli, "_run_claude", runner)
    out = cli.ClaudeCLIChat("haiku").with_structured_output(Toy).invoke([("human", "h")])
    assert out.score == 1
    assert calls["n"] == 2


def test_run_claude_strips_api_key_and_parses(monkeypatch):
    seen = {}

    class FakeProc:
        returncode = 0
        stdout = json.dumps({"is_error": False, "result": "答案"})
        stderr = ""

    def fake_run(args, **kwargs):
        seen["args"] = args
        seen["env"] = kwargs.get("env", {})
        return FakeProc()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-removed")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.shutil, "which", lambda name: "claude")
    out = cli._run_claude("hi", "haiku")
    assert out == "答案"
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert "--model" in seen["args"]


def test_run_claude_raises_on_error_envelope(monkeypatch):
    class FakeProc:
        returncode = 0
        stdout = json.dumps({"is_error": True, "result": "Invalid API key"})
        stderr = ""

    monkeypatch.setattr(cli.subprocess, "run", lambda args, **kw: FakeProc())
    monkeypatch.setattr(cli.shutil, "which", lambda name: "claude")
    with pytest.raises(RuntimeError):
        cli._run_claude("hi", "haiku")


def test_codex_structured_parses(monkeypatch):
    monkeypatch.setattr(cli, "_run_codex", lambda prompt: '{"name": "c", "score": 5}')
    out = cli.CodexCLIChat().with_structured_output(Toy).invoke([("human", "h")])
    assert out.name == "c" and out.score == 5
