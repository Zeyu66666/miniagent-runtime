
# 开发笔记

## 踩过的坑

### 1. 模型返回的 arguments 不是合法 JSON
- 现象：`json.loads` 抛 `JSONDecodeError`，整个任务崩
- 根因：模型在长参数里会漏引号或加注释
- 解法：`_parse_arguments` 返回 (dict, error)，错误回灌给模型让它自己修
- 效果：错误恢复成功率明显提升

### 2. tool 消息缺 tool_call_id
- 现象：400 `messages with role 'tool' must be a response to a preceding message`
- 根因：我用自增序号当 id，和模型给的 id 对不上
- 解法：严格使用 `call.id`

## 设计决策

### 为什么不用 LangChain
...

### 为什么 trace 用宽表 + JSON 而不是规范化的多张表
...

### 为什么只重试四类异常
...