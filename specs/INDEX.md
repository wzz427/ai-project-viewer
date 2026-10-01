# specs/INDEX —— 需求台账(唯一;同时是债务表的源账)

> 每个 SPEC 一行;**状态与"去处"的唯一真值 = 本表**(SPEC 正文不抄第二份)。
> 未立项的不占号;编号只增不复用;作废不删,状态写"已作废"+一行原因。
> Done 冷却后搬 `specs/archive/`,这里留一行索引。
> **本项目粒度:一段 = 一个 Phase(V1.5 §175–182),spec 编号与 Phase 号对齐**(spec-00N ↔ Phase N;依据 docs/workflow.md §五,2026-10-01)。

| 编号 | 标题(owner 会问的那句话) | 状态 | 去处(下一动作·归谁·什么时候) |
|---|---|---|---|
| spec-001 | 应用壳:开起来是什么样?(窗口、项目标签、加/删项目、主题) | Done | 已随 Phase 1 验收放行(2026-10-01 owner"继续下一个阶段开发");2026-10-01 应 owner 要求补全为完整 SPEC 形态;冷却后搬 specs/archive/ |
| spec-002 | 文件树、收藏置顶、文件识别怎么做? | Done | owner 验收通过(2026-10-01 原话"可以了,做spec003");冷却后搬 specs/archive/ |
| spec-003 | 文件打开与查看器:点一个文件能看到什么?(File Tabs / Markdown / Text / Code / JSON / Image / SVG + 五快捷键) | Done | owner 验收通过(2026-10-01 原话"这个就算过了吧");三轮返工全记录在本 SPEC §六;冷却后搬 specs/archive/ |
| spec-004 | Session & Settings:关掉再开,一切还在?(会话恢复+设置持久化+防抖原子写盘) | Ready | 免审门已过(workflow §五 A2);按 spec-004 §六切分⑤块开工,块①Rust state 模块起 |
