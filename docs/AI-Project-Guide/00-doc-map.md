# 00 · 文档体系总表 —— 项目每个阶段,该有/该建哪些文档

> **这是全书的心脏,先读这份。** 左列按项目阶段排(= 时间顺序),一个新仓库照着从上往下长。
> 每行:文档、它答什么、模板在哪。**没到那个阶段就不建那份文档**——
> 提前建 = 养一份空转的账(实例:没发版就建 changelog,被 owner 亲手删掉)。

---

## 阶段 0:仓库一建立(写第一行代码之前)

| # | 文档 | 答什么 | 模板 |
|---|---|---|---|
| 1 | **`AGENTS.md`** | 主文档:agent 的灵魂(怎么想、红线)+ 全部文档的路由表(干什么进哪份) | [`templates/AGENTS.md`](./templates/AGENTS.md) |
| 2 | **`demand.txt`** | **唯一权威需求源**:owner 的原始需求原话落盘;日后任何需求分歧回这里仲裁 | 不用模板,原话直接贴 |
| 3 | **`architecture.md` 的 §0「开发环境与跑法」** | 用哪个解释器、哪个包管理器、怎么装依赖、怎么启动、怎么跑测试、平台已知坑——**新 agent 不问人就能把项目跑起来** | [`templates/architecture.md`](./templates/architecture.md) |
| 4 | `docs/handoff.md` | 现在在哪、上一段为什么这么改(空账起步) | [`templates/handoff.md`](./templates/handoff.md) |
| 5 | `docs/lessons.md` | 踩坑全集(空账起步) | [`templates/lessons.md`](./templates/lessons.md) |
| 6 | `docs/history/INDEX.md` | 历史归档总目录(空账起步,先把"进 history 必登记"的规矩立好) | [`templates/history-INDEX.md`](./templates/history-INDEX.md) |
| 7 | `.gitignore`(密钥位)+ 备份 remote + 密钥红线立死 | 安全底线。⚠️ 备份 remote 需要 owner 提供——建不成就挂"要 owner 亲手做的"(handoff §三),建好当天首推+核 0;备份说明写在**主仓** `备份/README.md`(建 remote 那天)。**《密钥总备份》不第 0 天建**(零密钥项目不建空账),**首个密钥引入当天**建档。详见 [`07-backup-secrets.md`](./07-backup-secrets.md) | — |

## 阶段 1:总需求讨论(动第一行正式代码之前)

**动作**:与 owner 把总需求讨论清楚(怎么讨论见 [`01-startup.md`](./01-startup.md) §三),
产出两份文档:

| # | 文档 | 答什么 | 模板 |
|---|---|---|---|
| 8 | **`docs/spec.md`** 产品规格 | 产品"**做什么**":定位、目标用户、**站在使用者视角的完整使用流程**、功能清单(每条标将来落地它的 SPEC 号)。只写做什么,不写怎么做 | [`templates/spec.md`](./templates/spec.md) |
| 9 | **`architecture.md`** 填实 | 技术"**怎么做**":核心决策表(D 编号:选定方案+否决项+理由)、整体拓扑、代码地图、修订记录 | [`templates/architecture.md`](./templates/architecture.md) |

## 阶段 2:拆解(spec 定稿后、动手前)

| # | 文档 | 答什么 | 模板 |
|---|---|---|---|
| 10 | **`docs/roadmap.md`** | 需求拆解:分几批/几个里程碑、每批含哪些 SPEC 号、依赖顺序、每批的验收标准 | [`templates/roadmap.md`](./templates/roadmap.md) |
| 11 | **`specs/` 文件夹** + `INDEX.md` | 需求台账:每个 SPEC 一行(状态 + 去处),它同时是债务表的源账 | [`templates/specs-INDEX.md`](./templates/specs-INDEX.md) |
| 12 | `specs/SPEC-template.md` | 每个需求文档的起步骨架(规矩住台账 README 或 workflow) | [`templates/SPEC-template.md`](./templates/SPEC-template.md) |

## 阶段 3:逐个需求开发(specs/SPEC-NNN,项目的常态)

每个需求怎么过(讨论方案 → 技术方案 → 开发 → 自测交付)全在
[`02-dev-workflow.md`](./02-dev-workflow.md)。**随第一批需求长出来的文档**:

| # | 文档 | 什么时候建 | 答/管什么 | 模板 |
|---|---|---|---|---|
| 13 | **`docs/workflow.md`** | 第一个 SPEC 立项时 | **需求驱动开发的核心文档**:SPEC 状态机、每个跃迁的自检门、SPEC 模板规矩、归档规则 | [`templates/workflow.md`](./templates/workflow.md) |
| 14 | `docs/testing.md` | **第一个 SPEC 起草时**(Ready 的测试覆盖矩阵已经需要测法/耗时口径) | 测试规范:分级跑法、用例怎么从验证标准来、可视化验证规矩 | [`templates/testing.md`](./templates/testing.md) |
| 15 | **`docs/how-to-report.md`** | 第一次要向 owner 交付时 | **怎么汇报**:照着填的模板(标题=他会问的问题、固定句式、禁词表) | [`templates/how-to-report.md`](./templates/how-to-report.md) |
| 16 | `docs/doc-maintenance.md` | 第一个需求收口时 | 改了 X → 该同步哪些文档(底线三件套 + 同步总表) | [`templates/doc-maintenance.md`](./templates/doc-maintenance.md) |
| 17 | `docs/doc-routes.md` | **同一条规矩第二次被忘、或第一次因此返工时**(可客观判定的时点,别靠"感觉被忘了") | 路由表:什么动作发生时,自动把该看的规矩送到眼前 | [`templates/doc-routes.md`](./templates/doc-routes.md) |

## 阶段 4:运营期(多需求 / 多会话 / 上下文压缩出现后)

| # | 文档/机制 | 什么时候建 | 答/管什么 | 模板 |
|---|---|---|---|---|
| 18 | **`/wrap` 收尾命令** | 第一次上下文将满/owner 要 compact 时 | 压缩前的收尾:判时机→存盘→扫文档→落盘→报告(挂载方法见 [`05-handoff-wrap.md`](./05-handoff-wrap.md)) | [`templates/wrap.md`](./templates/wrap.md) |
| 19 | `docs/debts.md` | 待办开始散落、owner 问"还剩什么"答不准时 | 债务表:还欠什么、下一件动哪个(每笔带"去处") | [`templates/debts.md`](./templates/debts.md) |
| 20 | `docs/lessons-quickref.md` | lessons 大到全文 grep 费劲时 | 高频坑速查(只放指针) | [`templates/lessons-quickref.md`](./templates/lessons-quickref.md) |
| 21 | `docs/agents-board.md` | 第二个并发会话出现时 | 多会话工位板(谁在动什么,防互踩) | —(就一张表:日期\|会话\|在做什么\|占哪些文件;活干完删行) |

## 阶段 5:发版期

| # | 文档 | 什么时候建 | 答/管什么 | 模板 |
|---|---|---|---|---|
| 22 | `docs/changelog.md` | **第一次要发版时才建**(没发版建它=空转) | 每版对外改了啥;只留"开发中+最近两版",更早的滚动归档进 history | [`templates/changelog.md`](./templates/changelog.md) |
| 23 | 发版闸 + 转正总表 | 第一次打包前 | 打包前必过哪些检查;灰度→正式之间还差什么 | 见 [`03-testing.md`](./03-testing.md) §五 |
| 24 | `history/releases/` | 第一版发出后 | 版本轴归档:changelog 归档、发版快照(关键配置/提示词当时的样子) | 登记 `history/INDEX.md` |

## 总原则(建文档的三条判据)

1. **每份文档只答一个问题**;答别的问题的文档已经存在 → 加指针,不建新档。
2. **痛点出现才建**:每份文档对应一个真实的痛(忘了规矩→路由表;待办失控→债务表;
   上下文丢失→wrap)。**没有痛就建 = 空转的账 = 明天的熵。**
3. **建一份文档 = 同时决定它的回收方式**(它怎么变短、什么时候进 history)。
   决定不了回收方式的文档,先别建。

## 反模式清单(每一行都真实发生过)

- ❌ 没发版就建 changelog(空转,owner 亲手删过)
- ❌ 第一天就把"守卫生成器/路由钩子/工位板"全套搬齐(为没有病的病买药)
- ❌ 主文档写成手册(细则全塞进去 → 膨胀 → 没人读完 → 什么都不知道)
- ❌ 需求不编号、不写验证标准(后面测试用例无从写起,返工)
- ❌ 待办不带"去处"(列出来了没人做、没人发现没人做 = 埋坑)
