# Claude Code → OpenAI 兼容 API

把本机已登录的 **Claude Code CLI（Claude Max / Pro 订阅）** 包装成一个
OpenAI 协议兼容的 HTTP 服务，让任何支持 OpenAI 接口的工具（Cherry Studio、
NextChat、Open WebUI、`openai` SDK、LangChain、各类 IDE 插件等）都能直接
调用你的订阅，无需单独的 API Key、不按 token 计费。

> 原理：服务器把每个请求转成 `claude -p`（headless 模式）子进程调用。
> 也就是说，真正发请求的仍然是**官方 Claude Code 本体**，复用它已有的
> OAuth 登录态。

## 依赖

- 已安装并登录的 `claude` CLI（`claude` 能正常交互即可）
- Python 3.8+（仅用标准库，无需 `pip install`）

## 启动

```bash
python3 server.py
```

默认监听 `127.0.0.1:8787`。常用环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `HOST` | `127.0.0.1` | 监听地址，局域网共享用 `0.0.0.0` |
| `PORT` | `8787` | 端口 |
| `API_KEY` | 空 | 设置后客户端需带 `Authorization: Bearer <key>`；留空不鉴权 |
| `CLAUDE_DEFAULT_MODEL` | `sonnet` | 默认模型别名 |
| `CLAUDE_PERMISSION_MODE` | 空 | `default`/`acceptEdits`/`bypassPermissions`/`plan`/`dontAsk` |
| `CLAUDE_TIMEOUT` | `600` | 单次请求超时（秒） |
| `CLAUDE_BIN` | 自动探测 | claude 可执行文件路径 |

例：

```bash
HOST=0.0.0.0 PORT=8787 API_KEY=sk-mykey python3 server.py
```

## 接口

- `GET  /health` — 健康检查
- `GET  /v1/models` — 模型列表（`claude-code` / `sonnet` / `opus` / `haiku`）
- `POST /v1/chat/completions` — 对话，支持 `stream: true` 流式 SSE

### 非流式

```bash
curl http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"claude-code","messages":[{"role":"user","content":"你好"}]}'
```

### 流式

```bash
curl -N http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"sonnet","stream":true,"messages":[{"role":"user","content":"写首小诗"}]}'
```

### Python `openai` SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8787/v1", api_key="sk-mykey")  # 没设 API_KEY 时随便填
resp = client.chat.completions.create(
    model="claude-code",
    messages=[{"role": "user", "content": "用一句话解释什么是闭包"}],
)
print(resp.choices[0].message.content)
```

### 在客户端里配置（Cherry Studio / NextChat 等）

- API 地址 / Base URL：`http://127.0.0.1:8787/v1`
- API Key：随意填（除非你设了 `API_KEY`）
- 模型名：`claude-code` 或 `sonnet` / `opus` / `haiku`

## 模型映射

| 请求的 model | 实际调用 |
|--------------|----------|
| `claude-code`（或留空） | `CLAUDE_DEFAULT_MODEL`（默认 sonnet） |
| `sonnet` / `opus` / `haiku` | 对应别名 |
| 完整模型名，如 `claude-opus-4-8` | 原样透传 |

## 说明与限制

- **多轮对话**：每次请求会把 `messages` 全量历史拼成一个 prompt 传给 CLI，
  因此是无状态的——和 OpenAI 行为一致，上下文由客户端维护。
- **system 消息**：通过 `--append-system-prompt` 附加。
- **工具/权限**：默认不开放危险工具。如需让它读写文件、执行命令，设置
  `CLAUDE_PERMISSION_MODE`（注意安全，仅在可信环境使用）。
- **冷启动**：CLI 首次拉起约 1~2 秒，属正常现象。

## ⚠️ 关于使用条款（2026）

用本工具的方式是直接驱动**官方 `claude` CLI 本体**（而非提取 OAuth token
去裸调 Anthropic API），属于 Claude Code 自身的正常使用范畴。

但请注意：Anthropic 在 2026 年收紧了相关政策，明确限制把订阅额度
用于「第三方 harness / 自建客户端」。本工具仅供你**个人本地、自用**
场景参考；是否合规、会不会触发额度限制，请自行评估并以 Anthropic 最新
服务条款为准。请勿用于对外提供服务或商业转售。
