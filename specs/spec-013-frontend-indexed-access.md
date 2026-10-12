# SPEC-013-frontend-indexed-access —— 那 60 处"下标取空"隐患,清掉并把检查永久打开?(0.7.10)

> 状态:InDev —— **状态与"去处"的唯一真值 = INDEX.md 那一行**,本页不抄第二份。
> 创建:2026-10-12。Pre-Draft 出处:owner 原话"发版没那么急,先做这个需求,清掉这个问题"
> (指 spec-012 D12 记档项:L-c6 noUncheckedIndexedAccess 实测 60 错>止损线 20 未清)。

## 〇、值不值得做(两栏三出口,一行各一句)

- 好处:前端 8 文件 60 处"按下标取值、未防取到空"逐一见底(产线 22+测试 38);开关常开后
  此类隐患(下标越界→页面报错)编译期当场拦截,后续新增代码零成本受保护。
- 代价:60 处逐处判读+修,全档前端回归一轮+发体验版一轮;风险=守卫加错位置可能改变行为
  (用"行为零变化"门拦,见 V1)。
- 判:值→做(owner 已点名"先做这个需求",T3 缓)。

## 一、Pre-Draft 结论

- 核心选择题:开工时机=owner 拍"发版没那么急,先做这个"(T3/NSIS 顺延);修法分型见 D1。
- 标杆对照:TypeScript 官方 noUncheckedIndexedAccess 语义(索引访问返回 T|undefined);
  修法品味=能改结构不加断言,守卫优先于窄化。
- **界面确认**:N/A——纯类型层加固,零 UI 变化。

## 二、需求正文(R 编号;使用者视角)

> 穷尽性:本批无新触发器/状态/边界——全部是既有代码路径的类型层见底;
> 空态/加载/错误等维度由 V1 全档回归覆盖,不另立条目。

| R# | 需求(使用者视角) |
|---|---|
| R1 | 日常使用一切如旧:页签/树/PDF/会话恢复/并排 diff 的行为与 0.7.9 完全一致,使用者对本批无感知 |
| R2 | 工程免疫:`pnpm check` 在 noUncheckedIndexedAccess 常开下 0 错 0 警——此后新增代码里"下标取空"类隐患被编译器当场拦下 |

**反例规则(不许做什么)**:不借机重构/改任何行为;不为消错把类型改宽(禁止把 `T[]` 改成
`(T|undefined)[]` 迁就编译器);产线代码禁止无依据的裸 `!` 断言。

## 三、验证标准(V 编号;可判定)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1 | 全档回归数字不降:phase3 68+git 33+recent 15+r3 8+pdf 23+vitest 64 全绿;cargo 零改动免跑 | 自动 |
| V2 | R2 | tsconfig.json 含 `noUncheckedIndexedAccess: true` 且 `pnpm check` 0 错 0 警 | 自动 |
| V3 | R1 | 产线 22 处逐处可归型:守卫分支/结构改写/边界已证实的局部窄化,三者之一,清单落 §六 | 人工(清单核对) |
| V4 | R1/R2 | 版本三处 0.7.10;publish-experience.ps1 发体验渠道;发后核 exp 标识 | 自动 |

## 四、技术实现方案

**实测分布(2026-10-12,复跑与 spec-012 时点同数)**:

| 文件 | 处数 | 性质 |
|---|---|---|
| services/appState.test.ts | 28 | 测试 |
| services/diffSideBySide.test.ts | 10 | 测试 |
| components/Viewers/PdfViewer.svelte | 7 | 产线 |
| stores/tabsStore.svelte.ts | 6 | 产线 |
| stores/projectStore.svelte.ts | 3 | 产线 |
| services/diffSideBySide.ts | 3 | 产线 |
| stores/fileTreeStore.svelte.ts | 2 | 产线 |
| services/sessionRestore.svelte.ts | 1 | 产线 |

**修法分型(D1)**:每处三选一——A 结构改写(for-of / at() / 解构判空 / 查找式访问)优先;
B 边界已证实(长度刚判过/构造后即用)→局部窄化;C 测试文件允许显式非空断言
(夹具自造、炸=当场红)。tsconfig 开关本批常开。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 修法分型 A>B>C 如上;产线禁裸 `!` | 测试炸=当场红,产线炸=用户踩,宽严必须分层 | 全部统一允许 `!` | 产线断言=把隐患原地封存,开关白开 |
| D2 | freeze-guard 免跑 | 8 文件与 watcher 链零交集(watcherApply/watcherStore 未沾) | 照跑一轮 | 耗时档,触发条件明文未满足 |
| D3 | 版本 0.7.10,体验渠道交付 | 0.7.x 固定递增;owner 验收走 Update(SPEC-INFRA-001) | 只提交不发版 | owner 验收通道=体验渠道,不发没法验 |

**内存账**:零新增常驻——全部为类型层/局部守卫,无新数据结构、无新生命周期。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | 全档 e2e+vitest(数字见 V1) | AIV-TestProject+既有 | ⚠(方案) |
| R2 | V2 | tsconfig 断言+pnpm check | 无 | ⚠ |
| R1 | V3 | 产线 22 处修法归型清单人工核对 | 本 SPEC §六 | ⚠ |
| R1/R2 | V4 | 三处版本核+publish+exp 标识核 | 无 | ⚠ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-12 | Draft→Ready→InDev:自核 R/V 对齐(分布实测复跑 60/8 与记档一致);A2 开工对齐=owner 原话"发版没那么急,先做这个需求,清掉这个问题"(上一轮对话已说人话讲明范围=60 处、机械清、开关常开、行为零变化) | 本文档 |
| 2026-10-12 | InDev→InTest:60 处清零(修法归型见下),开关常开;全档回归=check 0/0+vitest 64/64+phase3 68/68+git 33/33+recent 15/15+r3 8/8+pdf 23/23;cargo/watcher 链零改动免跑(D2);0.7.10 发布体验渠道(update.json note 落盘;updates 二进制 UTF-16 VERSIONINFO=0.7.10+exp 标识,无 0.7.9 残留) | — |
| 2026-10-12 | **InTest→Done**:owner 验收通过,原话"过了。进入下一个需求"(V-human=owner 日常用一圈确认一切如旧);遗留零(60 处全清,开关常开) | — |

**V3 产线 22 处修法归型清单**(A=结构改写 / B=边界守卫或窄化;C=测试断言 38 处不逐列):

| 文件:处 | 型 | 一句话 |
|---|---|---|
| fileTreeStore reconcilePins ×2 | A | 解构 miss/add 判空替代 length===1 心算;顺手守卫 indexOf==-1 不再写 pinned[-1] |
| sessionRestore 激活兜底 ×1 | A | `.at(-1)` 判空替代 length>0 心算 |
| projectStore removeProject ×3 | B | findIndex 后取元素判空早退,forget×3 走局部 tab |
| tabsStore addOrActivate 循环 ×1 | A | 反向循环改 `findLastIndex((t)=>!t.pinned)` 等价改写 |
| tabsStore addOrActivate 替换 ×1 | B | replaced 三元守卫,cache 删与 splice 绑在同一真值上 |
| tabsStore moveTabToEnd ×1 | B | `if (moved)`(splice 单删必还一元) |
| tabsStore reorderTabs ×1 | B | `if (moved)` 同上 |
| tabsStore cycleTab ×2 | B | `if (!next) return`(模运算恒落界,守卫永不触发=纯窄化) |
| diffSideBySide diffPathOf ×1 | B | `split("\t")[0] ?? p`(split 恒≥1 元) |
| diffSideBySide hunk 头 ×2 | B | `parseInt(hunk[1] ?? "0")`(必匹配组;且 NaN 与 0 下游分支行为等价) |
| PdfViewer clampAt ×5 | B | `let row=rows[0]; if(!row) return`(rows.length===0 已判,一守卫窄化全表达式族) |
| PdfViewer runSearch ×1 | A | `const first=found[0]; if(first)` 替代 length>0 心算 |
| PdfViewer nextMatch ×1 | B | `const m=matches[matchIdx]; if(m)`(模运算恒落界) |
