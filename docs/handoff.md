# handoff —— 现在在哪 + 上一段为什么这么改

> 给下一个会话(或新人)的交接:**读完就知道"现在在哪、接着干啥"**,刻意短。
> 它不是日记,**更不是待办清单**——"还剩几件"住 debts.md(没有债务表的小项目,
> 待办住台账的"去处"列),这一页只装"发生了什么、为什么"。
>
> **怎么防胖 —— 整批回收,不是逐行削**:① 平时该加就加,别管行数;
> ② 发一版(或页面翻不动了,目测 300 行往上)把这批已完结的**整批蒸馏**进 history/progress/;
> **🚫 绝不"为了加一条删一条"——那样删掉的永远是最好删的那条。行数不设硬顶。**
> **写法**:每条只留"结论 + 下一步 + 去哪看全文";推导、实测原文留在它自己的 SPEC/报告里。

## 〇、现在主线是什么(最先读)

主线 = **Phase 2 File System & Favorites,Spec 已写好,等 owner 过目后开工**(Spec 全文:docs/specs/phase-2-file-system-and-favorites.md)。
Phase 1 已放行(2026-10-01 owner 原话"继续下一个阶段开发",按验收通过处理)。
下一步从哪接:owner 对 Spec 无异议(或改完 D1–D8 决策表)→ 说"开工"即按 Spec §六 提交切分执行,完成即停等验收(V1.5 §191 纪律不变)。

## 一、现在在哪(最新在上)

### 2026-10-01 · Phase 1 放行;立"每 Phase 先写 Spec"规矩,Phase 2 Spec 待过目

> **下一步从哪接** —— owner 看 docs/specs/phase-2-file-system-and-favorites.md(重点 §四 实现决策 D1–D8)→ 无异议说"开工";有异议改决策表再开工。

- owner 原话"继续下一个阶段开发" = Phase 1 验收放行;同轮立新规矩:每段开发先写 Spec 文档再开发(建仓时"不另建 specs/"的取舍就此推翻,§二 已留痕)。
- Spec 只装实现方案+决策+测试验收,需求真值仍在 V1.5(防复述漂移);Phase 1 不追溯补写。
- Playwright 正式化挂账顺延(原定"Phase 1 验收时顺带定",owner 未提,仍挂账区)。

### 2026-10-01 · Phase 1 Application Shell 交付,等 owner 验收

> **下一步从哪接** —— owner 验收(testing.md §2 末尾有 2 分钟手测路径)→ 通过后进 Phase 2(V1.5 §176,一次只做一个 Phase)。

- ⚠️ 验收中发现并已修复两件(2026-10-01,release 已重建,细节在 testing.md §2"验收反馈修复"):① Remove 入口原来只在顶栏标签右键,现 Files 面板项目路径右键也有(共享组件 ProjectContextMenu);② 全局禁用了 WebView 默认右键菜单(此前会露出 Back/Reload/Print/Inspect)。owner 需用新 exe 重验。
- Python 一律用 conda pywork 环境(owner 指定,architecture.md §0)。
- Tauri 2.12 + Svelte 5(纯 Vite,剥掉模板 SvelteKit)+ single-instance + dialog 插件;工程结构见 architecture.md §3。
- 实测全过:单实例 / 项目标签增删切去重(含原生 Picker 全链自动化)/ Files·Git·Settings 壳 / Theme / Ctrl+R 物理级拦截(WebView2 加速键已 COM 禁用,Tauri 2 无配置项,lessons L5)。
- Baseline:启动冷 992ms·温 88ms;进程树 Private 179MB(⚠️超 150 target,判读见 testing.md §3,Rust 主进程仅 5.9MB);空闲 CPU 0.35% 单核;WebView2 6 进程。
- GUI 自动化测试基建(CDP+UIA,无需前台)方法在 testing.md §1、踩坑在 lessons L3/L4/L6–L8,下次做 UI 验证直接复用。
- 测试目录 `%USERPROFILE%\aiv-test-projects\`(Alpha/Beta 空目录)留给 owner 验收用,用后可删。

### 2026-10-01 · 会话收口:owner 确认建仓,批准开工

> **下一步从哪接** —— 新会话按 AGENTS.md 开机三步进来,直接执行 V1.5 §192(仅 Phase 1,完成即停等验收)。

- owner 拍板两件:① 初始化验收通过,批准进入 Phase 1 开发;② 异地备份不着急,V1 全部做完、owner 验收后再建(挂账已改期)。

### 2026-10-01 · Rust 工具链安装完毕,Phase 1 前提全部就绪

> **下一步从哪接** —— owner 确认后按 V1.5 §192 开始 Phase 1;开发环境已无阻塞项(备份 remote 仍是 owner 挂账)。

- rustup 用户级安装 rustc/cargo 1.98.1(msvc),VS 2022 Build Tools 已存在提供链接器,hello-world 编译运行验证通过。
- tauri-cli 决定用 pnpm 的 @tauri-apps/cli(JS 版,Phase 1 随脚手架安装),不装 cargo tauri-cli(免 10 分钟级本地编译)。

### 2026-10-01 · 建仓(按 AI-Project-Guide 阶段 0)

> **下一步从哪接** —— owner 确认建仓结果后,按 V1.5 §192 开始 Phase 1;先装 Rust 工具链,再输出工程结构与风险清单,只做 Phase 1。

- 需求经 V1.1→V1.5 五轮评审定稿,V1.5 FINAL 为唯一基线;旧版已删;
  V1.5 尾部 §196 为 ZCode 评审附注(附注 A 是 git 路径基准的事实性修正,Phase 7 前合入正文)。
- 本次建立:AGENTS.md / demand.txt / architecture.md(§0 环境已实测,D1–D9 决策已落表)/ 三份空账 / .gitignore / 首笔 commit。
- 环境实测:Node 24.14 + pnpm 11.1 ✅;**Rust 未安装** ❌(详见 architecture.md §0)。

## 二、为什么这么改(当批关键取舍;只在"后人容易被顺手的改法改回去"处留一句)

- **~~不另建 spec.md / roadmap.md / specs/~~**(2026-10-01 改口,出处:owner"每一段开发都要专门写一个 Spec 文档再开发"):
  现规矩 = **每个 Phase 开工前先写 `docs/specs/phase-N-*.md`**(实现方案+实现决策+测试验收,需求真值仍只在 V1.5,Spec 只挂指针)。
  原取舍(V1.5 兼任 spec、待痛点出现再建)低估了"owner 要在动代码前审得到实现方案"这一痛点;roadmap 职能仍由 V1.5 独占,不变。
- **需求变更走增量修订 + 变更审计(V1.5 §193),禁止整篇重写**:V1.2→V1.3→V1.4 三次整篇重写
  每次都丢过已确认规格,V1.5 起改为"只改明确条目+审计清单"后未再发生回归。

## 三、挂账区:等 owner 的事 + 非 SPEC 零散待办(一行一件,带去处)

> 债务表(debts.md)未建的阶段,这里就是**全部待办的家**;待办散落/约超 10 条 → 该建 debts.md。

| 事 | 去处(归谁·什么时候) | 提出日期 |
|---|---|---|
| 建异地备份 remote(私有库,SSH 认证),建好当天首推+核 0;建立之前仓库只有本地一份 | owner 亲手(AI-Project-Guide 07)·**V1 全部完成后、owner 验收时**(2026-10-01 owner 拍板改期,不着急) | 2026-10-01 |
| V1.5 §196 附注 A(git -C 统一执行基准)合入 §65 正文 | agent·Phase 7 前 | 2026-10-01 |
| Playwright 回归脚本正式化入库(pywork 环境跑,替代 %TEMP% 手搓脚本;方案已口头验证可行) | agent·**等 owner 点头**(Phase 1 验收时顺带定;点头后约 30 分钟) | 2026-10-01 |
