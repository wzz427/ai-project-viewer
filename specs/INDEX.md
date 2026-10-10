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
| spec-004 | Session & Settings:关掉再开,一切还在?(会话恢复+设置持久化+防抖原子写盘) | Done | owner 验收通过(2026-10-01 原话"通过了");Done 后同日补侧栏拖拽(owner 拍板"要拖拽",D6 翻案留痕,回归 7/7);冷却后搬 specs/archive/ |
| spec-005 | PDF.js Spike:点一个 PDF 能看到什么?(验证→首页→完整查看器→Benchmark) | Done | owner 验收通过(2026-10-10 原话"0.4.1 已经过了");四轮划词收口(155 升级/色块/蔓选/反选)全毕;冷却后搬 specs/archive/ |
| SPEC-INFRA-001 | 体验版客户端与更新机制:开发永远不碰 owner 正在用的程序(更新按钮置灰/高亮/一点更新) | Done | owner 验收通过(2026-10-10;v6→0.4.1 十余轮更新按钮实走,原话"0.4.1 已经过了");冷却后搬 specs/archive/ |
| SPEC-INFRA-002 | 应用图标:换掉 Tauri 默认 logo(「项目检视」:白文件夹+放大镜) | Done | owner 验收通过(2026-10-10 原话"收口吧";桌面/任务栏显示缓存问题当日已现场修复);冷却后搬 specs/archive/ |
| SPEC-INFRA-003 | 文本查看器统一操作栏(字号+Find)+ MD 文本铺满 | Done | owner 验收通过(2026-10-10 原话"收口吧");两轮返工全记录在本 SPEC(上限删除翻案/工具栏同高/断言对齐原话);冷却后搬 specs/archive/ |
| spec-006 | Phase 6 Handoff:右键移交外部工具(记事本/VS Code/资源管理器/浏览器/复制路径) | Done | owner 验收通过(2026-10-10 原话"收口吧,我准备开新对话,做下一个需求");0.6.2–0.6.6 五版四轮返修全记录在本 SPEC §六;冷却后搬 specs/archive/ |
| spec-007 | Phase 7 Git Review:改了什么、跟远端差多少,一眼看完(只看不改) | Done | 0.6.7 首发+0.6.8 返修轮(面板照 VS Code 重排/提交详情/并排 diff),owner 验收通过(2026-10-10,"这个需求通过了");打磨项(折叠条展开/行内高亮)记 §四 D17 |
| spec-008 | Phase 8 RUN/Trust:脚本/EXE 可见控制台运行+项目信任门+Executable Info+URL 白名单接线 | InTest | 0.6.9 首发+0.6.10 守卫+0.6.11 页签归还+0.6.12(右键高亮/demo.exe 真程序/信任文案/诊断导出);phase3 58/git 32 其余全绿;内容区冻结 bug 未结(诊断已装,等 owner 触发取证) |
