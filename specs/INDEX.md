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
| spec-008 | Phase 8 RUN/Trust:脚本/EXE 可见控制台运行+项目信任门+Executable Info+URL 白名单接线 | Done | owner 验收通过(2026-10-11 原话"这期收口,进下一个需求,版本升到0.7");0.6.9 首发+0.6.10–0.6.13 四轮返修全记录在本 SPEC §六;内容区冻结 bug 未结→handoff 挂账(诊断已装等取证);冷却后搬 specs/archive/ |
| spec-009 | Phase 9 Watcher:文件变了自动刷(树/正在看的文件/Git),删改名的页签与置顶跟着走 | Done | owner 验收通过(2026-10-11 收口原话"我换新对话做下一个需求";0.7.2 换装后持续使用至 0.7.5 无再报卡死);0.7.0 首发+0.7.1/0.7.2 两轮返修记录在本 SPEC §六;冷却后搬 specs/archive/ |
| spec-010 | Open Recent:加项目时一键找回最近打开过的文件夹(owner 2026-10-11 增量需求,V1.5 §198;Phase 10 §184 顺延为 spec-011) | Done | owner 验收通过(2026-10-11 同收口指令;在用佐证:0.7.4"行号对齐了"+0.7.5 字号诉求均针对其交付链);单轮 0.7.3;冷却后搬 specs/archive/ |
| spec-011 | Phase 10 上线前体检:查性能漏(九类)+查安全隐患(十一类)+定发版方式(规划内最后开发阶段,§184;禁新增产品功能) | InTest | 2026-10-11 A2 对齐(owner"开工")→同日 InDev→InTest:0.7.6 首发+0.7.7 返修(工具栏双击变蓝,L40);code review 修复批 spec-012 已 Done(报告归 history/code-reviews/)→**下一动作=T3 全量基准(owner 已预告授权,开跑前按红线再确认一次)**→复验通过即 Done;NSIS 打包仍须届时点头(webviewInstallMode 三选一) |
| spec-012 | code review 修复批:查出的 44 个问题全都修掉?(0.7.8,关联 history/code-reviews/code-review-2026-10-11.md) | Done | 2026-10-11 一批修完 43 条(42 落地+L-c6 触发止损记档,记档去处=下一前端专项批次 D12)→0.7.8 发体验渠道;2026-10-12 InTest 报障返修 0.7.9(右键动作后高亮跳回,L41);同日 owner 验收通过(原话"spec012可以done"),评审报告已归 history/code-reviews/;冷却后搬 specs/archive/ |
| spec-013 | 前端加固:60 处"下标取空"隐患清掉+索引访问检查常开(0.7.10;spec-012 D12 记档项的清偿批次) | InTest | 2026-10-12 一批修完 60 处(产线 22 守卫/结构改写+测试 38 显式断言,归型清单住 SPEC §六),开关常开;全档回归全绿(check 0/0+vitest 64+phase3 68+git 33+recent 15+r3 8+pdf 23;cargo/watcher 零改动免跑 D2)→0.7.10 已发体验渠道——**等 owner 点 Update 验收**;验收原话落 §六→Done;随后回 T3 主线(spec-011) |
