
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


┏━━━━━━━━━━━━┳━━━━━━━┓
┃ 指标       ┃    值 ┃
┡━━━━━━━━━━━━╇━━━━━━━┩
│ 任务数     │    40 │
│ 通过       │    37 │
│ 成功率     │ 92.5% │
│ 平均 token │  3280 │
│ 平均步数   │  6.03 │
└────────────┴───────┘


失败 3 条：
  m08 文件不存在：D:\project1\miniagent-runtime\eval\workspace\summary.txt
  m09 文件不存在：D:\project1\miniagent-runtime\eval\workspace\big.txt
  m10 文件不存在：D:\project1\miniagent-runtime\eval\workspace\features.txt



| id | 任务 | 原因 |
|---|---|---|
| m08 | 创建文件 summary.txt，内容写入 notes.txt 里的项目代号。完 | 文件不存在：D:\project1\miniagent-runtime\eval\workspace\summary.txt |
| m10 | 读 config.json，把 features 数组的每个元素单独一行写入 f | 文件不存在：D:\project1\miniagent-runtime\eval\workspace\features.txt |
| m14 | 读 numbers.csv，把每行的 name 转成大写，写入 upper.tx | 文件不存在：D:\project1\miniagent-runtime\eval\workspace\upper.txt |
| s03 | notes.txt 里写的上线日期是哪一天？ | 答案中缺少 '2026-03-15'；实际答案：'上线日期是 2026 年 3 月 15 日。' |
| s12 | bug.log 里最后一次 ERROR 的原因是什么？用一句话说。 | 答案中缺少 'timeout'；实际答案：'最后一次 ERROR（10:22:41）的原因是**上游请求在 5000ms 后超时**，之后熔断器被打开了。' |


忘记把写文件工具加入了
修改工具调用逻辑read_file 的报错附带候选文件名后，模型反而更爱重试读文件 回滚后重做


# 评测报告 · 2026-10-24 16:27:38

- 任务数：**40**
- 通过：**40**
- 成功率：**100.0%**
- 平均 input token：**3701**
- 平均步数：**5.65**

## 失败清单

全部通过。
