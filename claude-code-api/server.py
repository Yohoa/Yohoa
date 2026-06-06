#!/usr/bin/env python3
"""
Claude Code -> OpenAI 兼容 API 服务器

把本机已登录的 `claude` CLI 包装成一个 OpenAI 兼容的 HTTP 接口，
任何支持 OpenAI 协议的客户端（Cherry Studio / NextChat / openai SDK /
LangChain 等）都可以直接连接使用。

启动:
    python3 server.py
    # 或自定义端口/鉴权
    HOST=0.0.0.0 PORT=8787 API_KEY=sk-mykey python3 server.py

支持的接口:
    GET  /v1/models
    POST /v1/chat/completions   (支持 stream=true 流式 SSE)
    GET  /health

仅依赖 Python 标准库，无需安装任何第三方包。
"""

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# 配置 (全部可通过环境变量覆盖)
# ---------------------------------------------------------------------------
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8787"))
# 若设置则要求客户端携带 Authorization: Bearer <API_KEY>; 留空表示不鉴权
API_KEY = os.environ.get("API_KEY", "")
# claude 可执行文件路径
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", shutil.which("claude") or "claude")
# 默认模型别名 (sonnet / opus / haiku 或完整模型名)
DEFAULT_MODEL = os.environ.get("CLAUDE_DEFAULT_MODEL", "sonnet")
# 权限模式: default / acceptEdits / bypassPermissions / plan / dontAsk
# 作为 API 使用时通常希望它能自主完成, 但开放工具有风险, 默认 default。
PERMISSION_MODE = os.environ.get("CLAUDE_PERMISSION_MODE", "")
# 单次请求超时(秒)
TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT", "600"))
# 暴露给 /v1/models 的模型列表
MODELS = ["claude-code", "sonnet", "opus", "haiku"]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def map_model(requested):
    """把客户端请求的模型名映射成 claude CLI 接受的别名/模型名。"""
    if not requested or requested == "claude-code":
        return DEFAULT_MODEL
    return requested


def messages_to_prompt(messages):
    """
    把 OpenAI 风格的 messages 数组拆分为:
      - system_prompt: 拼接所有 system 消息
      - prompt: 其余对话整理成纯文本(带角色标签), 作为单次 prompt 传给 claude
    这样可以无状态地承载完整对话历史(OpenAI 客户端每次都会带全量历史)。
    """
    system_parts = []
    convo_parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        # content 可能是字符串, 也可能是 OpenAI 的多模态数组
        if isinstance(content, list):
            text_chunks = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_chunks.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_chunks.append(part)
            content = "\n".join(text_chunks)
        content = str(content)

        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            convo_parts.append(f"Assistant: {content}")
        elif role == "tool":
            convo_parts.append(f"Tool result: {content}")
        else:  # user 及其它
            convo_parts.append(f"User: {content}")

    system_prompt = "\n\n".join(system_parts).strip()

    # 如果只有一条 user 消息, 直接用原文, 不加角色标签, 体验更自然
    user_only = [m for m in messages if m.get("role") not in ("system",)]
    if len(user_only) == 1 and user_only[0].get("role") == "user":
        c = user_only[0].get("content", "")
        if isinstance(c, list):
            c = "\n".join(
                p.get("text", "") for p in c
                if isinstance(p, dict) and p.get("type") == "text"
            )
        prompt = str(c)
    else:
        prompt = "\n\n".join(convo_parts)
        if convo_parts and convo_parts[-1].startswith("User:"):
            prompt += "\n\nAssistant:"

    return system_prompt, prompt


def build_cmd(model, output_format, system_prompt):
    cmd = [CLAUDE_BIN, "-p", "--model", model, "--output-format", output_format]
    if output_format == "stream-json":
        cmd += ["--include-partial-messages", "--verbose"]
    if system_prompt:
        cmd += ["--append-system-prompt", system_prompt]
    if PERMISSION_MODE:
        cmd += ["--permission-mode", PERMISSION_MODE]
    return cmd


# ---------------------------------------------------------------------------
# 调用 claude CLI
# ---------------------------------------------------------------------------
def run_claude_blocking(model, system_prompt, prompt):
    """非流式: 调用 claude 一次, 返回完整文本。"""
    cmd = build_cmd(model, "json", system_prompt)
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited with code {proc.returncode}: {proc.stderr.strip()}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        # 兜底: 直接当纯文本返回
        return proc.stdout.strip(), None
    text = data.get("result", "") if isinstance(data, dict) else str(data)
    usage = data.get("usage") if isinstance(data, dict) else None
    return text, usage


def run_claude_stream(model, system_prompt, prompt):
    """
    流式: 调用 claude --output-format stream-json, 逐行解析,
    yield 出新增的文本增量 (delta)。
    """
    cmd = build_cmd(model, "stream-json", system_prompt)
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    proc.stdin.write(prompt)
    proc.stdin.close()

    emitted = ""  # 已经发送给客户端的累计文本
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = evt.get("type")

            # 最终 result 事件: 用它来补齐可能漏掉的尾部文本
            if etype == "result":
                final = evt.get("result", "")
                if final and final.startswith(emitted) and len(final) > len(emitted):
                    yield final[len(emitted):]
                    emitted = final
                continue

            # assistant 消息事件: 包含完整的当前文本, 计算增量
            if etype == "assistant":
                msg = evt.get("message", {})
                text = ""
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")
                if text and text.startswith(emitted):
                    delta = text[len(emitted):]
                    if delta:
                        yield delta
                        emitted = text
                elif text and not emitted:
                    yield text
                    emitted = text

            # 流式增量事件 (--include-partial-messages)
            elif etype == "stream_event":
                ev = evt.get("event", {})
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunk = delta.get("text", "")
                        if chunk:
                            yield chunk
                            emitted += chunk
    finally:
        proc.stdout.close()
        rc = proc.wait(timeout=TIMEOUT)
        if rc != 0:
            err = proc.stderr.read().strip()
            if err and not emitted:
                raise RuntimeError(f"claude exited with code {rc}: {err}")


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- 辅助 ----
    def _check_auth(self):
        if not API_KEY:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {API_KEY}"

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code, message, etype="invalid_request_error"):
        self._send_json(code, {"error": {"message": message, "type": etype}})

    def _sse_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _sse_send(self, obj):
        self.wfile.write(f"data: {json.dumps(obj, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()

    # ---- 路由 ----
    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "claude": CLAUDE_BIN})
            return
        if self.path.rstrip("/") == "/v1/models":
            if not self._check_auth():
                self._send_error(401, "Invalid API key", "authentication_error")
                return
            now = int(time.time())
            self._send_json(200, {
                "object": "list",
                "data": [
                    {"id": m, "object": "model", "created": now, "owned_by": "claude-code"}
                    for m in MODELS
                ],
            })
            return
        self._send_error(404, f"Not found: {self.path}")

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send_error(404, f"Not found: {self.path}")
            return
        if not self._check_auth():
            self._send_error(401, "Invalid API key", "authentication_error")
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON body")
            return

        messages = payload.get("messages", [])
        if not messages:
            self._send_error(400, "`messages` is required")
            return

        model = map_model(payload.get("model"))
        stream = bool(payload.get("stream", False))
        system_prompt, prompt = messages_to_prompt(messages)

        completion_id = "chatcmpl-" + uuid.uuid4().hex
        created = int(time.time())

        if stream:
            self._handle_stream(completion_id, created, model, system_prompt, prompt)
        else:
            self._handle_blocking(completion_id, created, model, system_prompt, prompt)

    # ---- 非流式 ----
    def _handle_blocking(self, cid, created, model, system_prompt, prompt):
        try:
            text, usage = run_claude_blocking(model, system_prompt, prompt)
        except subprocess.TimeoutExpired:
            self._send_error(504, "claude timed out", "timeout")
            return
        except Exception as e:  # noqa: BLE001
            self._send_error(500, str(e), "api_error")
            return

        u = {}
        if isinstance(usage, dict):
            pt = usage.get("input_tokens", 0)
            ct = usage.get("output_tokens", 0)
            u = {"prompt_tokens": pt, "completion_tokens": ct,
                 "total_tokens": pt + ct}
        self._send_json(200, {
            "id": cid,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
            "usage": u,
        })

    # ---- 流式 ----
    def _handle_stream(self, cid, created, model, system_prompt, prompt):
        self._sse_headers()
        base = {"id": cid, "object": "chat.completion.chunk",
                "created": created, "model": model}

        # 首个 chunk: 角色
        self._sse_send({**base, "choices": [
            {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]})

        try:
            for delta in run_claude_stream(model, system_prompt, prompt):
                self._sse_send({**base, "choices": [
                    {"index": 0, "delta": {"content": delta}, "finish_reason": None}]})
        except Exception as e:  # noqa: BLE001
            self._sse_send({**base, "choices": [
                {"index": 0, "delta": {"content": f"\n[error] {e}"},
                 "finish_reason": None}]})

        # 结束 chunk
        self._sse_send({**base, "choices": [
            {"index": 0, "delta": {}, "finish_reason": "stop"}]})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main():
    if not shutil.which(CLAUDE_BIN) and not os.path.exists(CLAUDE_BIN):
        sys.stderr.write(f"[警告] 找不到 claude 可执行文件: {CLAUDE_BIN}\n")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    auth = "已启用 (需 Bearer Key)" if API_KEY else "未启用"
    print(f"""
Claude Code OpenAI 兼容 API 已启动
  地址:     http://{HOST}:{PORT}/v1
  模型:     {', '.join(MODELS)}  (默认 -> {DEFAULT_MODEL})
  鉴权:     {auth}
  claude:   {CLAUDE_BIN}

示例:
  curl http://{HOST}:{PORT}/v1/chat/completions \\
    -H 'Content-Type: application/json' \\
    -d '{{"model":"claude-code","messages":[{{"role":"user","content":"你好"}}]}}'

按 Ctrl+C 停止。
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭...")
        server.shutdown()


if __name__ == "__main__":
    main()
