# agymcp

将 [Antigravity CLI (agy)](https://antigravity.dev) 包装为 MCP Server，供 Claude Code 等支持 MCP 协议的客户端调用。

## 前置条件

- [Antigravity CLI](https://antigravity.dev) 已安装并完成登录（`agy` 命令在 PATH 中可用）
- [uv](https://github.com/astral-sh/uv) 已安装（用于 uvx 拉取运行）

## 安装

在 `~/.claude.json` 的 `mcpServers` 中添加：

```json
{
  "mcpServers": {
    "agy": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/leologoli/agymcp.git",
        "agymcp"
      ],
      "env": {},
      "type": "stdio"
    }
  }
}
```

重启 Claude Code 后生效，首次启动会自动拉取安装依赖。

## 工具说明

### `agy`

调用 Antigravity CLI 执行 AI 任务，返回模型回复文本和会话 ID。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `PROMPT` | string | ✅ | 发送给 Antigravity 的任务指令 |
| `cd` | path | ✅ | 执行任务时的工作目录（workspace root） |
| `SESSION_ID` | string | ❌ | 续话会话 ID，为空时开启新会话 |
| `sandbox` | bool | ❌ | 是否启用沙箱模式，默认 false |
| `model` | string | ❌ | 指定模型，留空使用默认模型 |

**返回：**

| 字段 | 说明 |
|------|------|
| `success` | 是否成功 |
| `SESSION_ID` | 会话 UUID，传入下次调用可续话 |
| `agent_messages` | 模型回复文本 |
| `error` | 失败时的错误描述 |

**示例：**

```json
// 新建会话
{
  "PROMPT": "用一句话介绍你自己",
  "cd": "/path/to/project"
}

// 续话
{
  "PROMPT": "我上一条问你什么了？",
  "cd": "/path/to/project",
  "SESSION_ID": "56540478-7163-4d90-a476-f2487c81aa6a"
}
```

## 实现原理

1. 以 `--print` 模式运行 `agy`，通过 `--log-file` 将日志写入临时文件
2. 从日志中正则提取 `conversation UUID` 作为 `SESSION_ID`
3. 续话时通过 `--conversation <SESSION_ID>` 参数恢复上下文
4. 基于 [FastMCP](https://github.com/jlowin/fastmcp) 实现 stdio 传输

## License

MIT
