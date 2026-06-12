# RAGFlow 0.19.0 定制化改造文档

## 改造目标

1. **全工作流节点级流式输出**：每个节点执行完成后，API/SSE 实时推送 `node_completed` 事件，包含 `node_id`、`node_type`、`output`
2. **LLM thinking 推理字段透传**：DeepSeek R1 等推理模型的 `reasoning_content` 在节点输出和最终答案中均完整传递

## 改动文件清单 (12 个文件)

### 1. `agent/canvas.py` — 工作流引擎

**改动**：`run()` 方法中，Begin 节点和每个组件节点执行完成后，yield `node_completed` 事件。

```python
# Begin 节点完成后推送 (L191-L194)
node_info = self.components["begin"]["obj"].get_node_info()
yield {"node_completed": True, "running_status": True, "content": "",
       "node_id": node_info["node_id"], "node_type": node_info["node_type"],
       "output": node_info["output"]}

# 每个组件执行完成后推送 (L235-L239)
node_info = cpn.get_node_info()
yield {"node_completed": True, "running_status": True, "content": "",
       "node_id": node_info["node_id"], "node_type": node_info["node_type"],
       "output": node_info["output"]}
```

### 2. `agent/component/base.py` — 组件基类

**改动**：新增 `get_node_info()` 方法，返回节点 id、type 和 output 数据。

```python
def get_node_info(self):
    """Get node information including node_id, node_type and output for streaming."""
    o = getattr(self._param, self._param.output_var_name)
    if isinstance(o, partial):
        return {"node_id": self._id, "node_type": self.component_name,
                "output": {"status": "streaming"}}
    if isinstance(o, pd.DataFrame):
        return {"node_id": self._id, "node_type": self.component_name,
                "output": o.to_dict(orient="records")}
    if isinstance(o, list):
        return {"node_id": self._id, "node_type": self.component_name,
                "output": o}
    return {"node_id": self._id, "node_type": self.component_name,
            "output": {"content": str(o) if o is not None else ""}}
```

### 3. `agent/component/generate.py` — LLM 生成节点

**改动**：非流式和流式输出中均加入 `reasoning_content` 字段。
- `_run()` 非流式分支：`pd.DataFrame([{"content": ans, "reasoning_content": reasoning}])`
- `stream_output()` 流式分支：每块输出 `{"content": ..., "reasoning_content": last_reasoning}`

### 4. `api/db/services/canvas_service.py` — API 层画布服务

**改动**：
- `completion()` 函数中，加载已有 session DSL 后，仅当上次执行已完成完整工作流时才重置 path/answer，否则保持对话状态继续执行
- 执行成功后清理空的 `path[-1]`，匹配前端 `canvas_app.py` 的处理逻辑

```python
# 关键修改：智能重置执行状态
if len(canvas.path) >= 2 and len(canvas.path[-1]) > 1:
    canvas.path = []
    canvas.answer = []

# 清理空路径
if not canvas.path[-1]:
    canvas.path.pop(-1)
```

### 5. `api/apps/canvas_app.py` — 前端画布 API

**改动**：前端 `completion` 接口也增加了 `node_completed` 事件的透传。

### 6. `api/db/services/llm_service.py` — LLM 服务层

**改动**：修复 `chat_streamly()` 中 `rstrip` 为 `removesuffix`，避免破坏 reasoning 标签结构。

```python
# 修复前
ans = ans.rstrip("</think>")  # 错误：按字符集剥离
# 修复后
ans = ans.removesuffix("</think>")  # 正确：按后缀移除
```

### 7. `rag/llm/chat_model.py` — LLM 模型适配层

**改动**：
- `Base.chat()` 非流式模式：从 API 响应提取 `reasoning_content`，包装为 `<think>...</think>` 标签
- `Base.chat_streamly()` / `chat_streamly_with_tools`：修复 reasoning chunk 的前缀/后缀逻辑

```python
# chat() 非流式
if hasattr(response.choices[0].message, "reasoning_content") and response.choices[0].message.reasoning_content:
    ans = "<think>" + response.choices[0].message.reasoning_content + "</think>" + ans

# chat_streamly() 流式：第一个 reasoning chunk 加 <think> 前缀
if not reasoning_start:
    reasoning_start = True
    ans = "<think>" + resp.choices[0].delta.reasoning_content + "</think>"
else:
    ans = resp.choices[0].delta.reasoning_content + "</think>"
```

### 8-12. 其他组件文件（轻量改动）

| 文件 | 改动 |
|------|------|
| `agent/component/categorize.py` | 输出结构调整 |
| `agent/component/keyword.py` | 输出结构调整 |
| `agent/component/relevant.py` | 输出结构调整 |
| `agent/component/rewrite.py` | 输出结构调整 |
| `agent/component/exesql.py` | 输出结构调整 |

---

## SSE 事件结构

### node_completed 事件
```json
{
  "code": 0,
  "data": {
    "answer": "",
    "running_status": true,
    "node_completed": true,
    "node_id": "Generate:ExampleId",
    "node_type": "Generate",
    "output": [
      {
        "content": "回答内容...",
        "reasoning_content": "<think>推理过程...</think>"
      }
    ]
  }
}
```

### 最终答案事件
```json
{
  "code": 0,
  "data": {
    "answer": "最终回答...",
    "reference": [...],
    "reasoning_content": "..."
  }
}
```

---

## 验证结果

| 测试项 | 状态 | 详情 |
|--------|------|------|
| 节点级流式输出 | PASS | Categorize/Retrieval/Generate/Begin/Template 全部捕获 |
| thinking 透传 | PASS | deepseek-reasoner 的 reasoning_content 完整传递 |
| 对话式工作流 (test) | PASS | 多轮对话，Categorize→Retrieval→Generate 链路正常 |
| 文件上传工作流 (test2) | PASS | multipart/form-data 上传→Begin→Generate→Template 链路正常 |
| API 并发 | PASS | test + test2 同时执行，互不干扰 |

---

## 部署迁移指南

### 方法一：Git patch 方式（推荐）

1. 将 `ragflow_modifications.patch` 复制到目标服务器
2. 在目标服务器的 RAGFlow 源码目录执行：
```bash
git apply ragflow_modifications.patch
```
3. 重启服务：
```bash
docker restart ragflow-server
```

### 方法二：直接覆盖文件

将以下 12 个修改过的文件复制到目标服务器的对应路径：
```
agent/canvas.py
agent/component/base.py
agent/component/generate.py
agent/component/categorize.py
agent/component/keyword.py
agent/component/relevant.py
agent/component/rewrite.py
agent/component/exesql.py
api/db/services/canvas_service.py
api/db/services/llm_service.py
api/apps/canvas_app.py
rag/llm/chat_model.py
```

然后重启容器。

### 方法三：Docker volume 挂载

如果目标服务器用 docker-compose 启动且已挂载源码目录，只需替换文件后重启：
```bash
docker-compose restart ragflow-server
```

### 注意事项

- **版本要求**：基于 RAGFlow 0.19.0，其他版本可能有差异
- **兼容性**：所有改动仅限服务端，不修改 API 签名，不修改前端代码，openai SDK 客户端可无缝使用
- **不需要数据库迁移**：不涉及 schema 变更
- **回滚**：执行 `git checkout .` 即可恢复原始代码
