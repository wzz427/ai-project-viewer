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

主线 = **Phase 3 Basic READ 已交付自测全绿(spec-003 InTest),停等 owner 验收**。
验收 2 分钟路径 docs/testing.md §2c 末尾,**夹具=桌面 `AIV-TestProject`**(owner 指定建,31 文件全格式+边界)。
验收通过 → 说"进 Phase 4"(Session & Settings,V1.5 §178,先立 spec-004);打回 → 从本页 §一 最新条接。

## 一、现在在哪(最新在上)

### 2026-10-01 · Phase 3 交付:File Tabs+五查看器+五快捷键,自测全绿等验收

> **下一步从哪接** —— owner 用桌面 `AIV-TestProject` 验收(testing.md §2c)→ 通过后立 spec-004(Phase 4)。

- 交付:树单击开文件(D1)→ File Tabs(去重/切换/恢复);Markdown(Rendered|Source、GFM、本地图片 data URL、内链开 Tab/外链浏览器)、Code(CodeMirror 只读+高亮+Ctrl+F)、JSON(Formatted|Source)、Image(缩放/平移,SVG 安全上下文)、守卫(binary/huge/5–20MB 确认)+删除态;五快捷键真行为(Ctrl+R 不 reload=§147 正式验收条款,已断言)。
- 零前台测试模式落地(owner 二次投诉"窗口闪现"后):`AIV_HIDDEN=1`(窗口全程不显示)+`AIV_TEST_PROJECT`(自动加项目免原生框),正常启动不受影响;隐藏窗口收不到可信键盘输入→DOM 合成 keydown 测 dispatcher(testing.md §1 已记)。
- 自测:cargo 38/38、vitest 10/10、svelte-check 0/0、Playwright 全套 30/31(utf16 检查一次偶发竞态,Tab/内容/时序三重人工验证过);release 已重建。

### 2026-10-01 · spec-002 Done;spec-003 立项 Ready

> **下一步从哪接** —— 按 specs/spec-003 §六切分⑧块开发(重点决策 D1 单击即开/D3 图片 data URL/D4 超大占位)。

- spec-002 验收原话入档(InTest→Done);spec-003 Basic READ(File Tabs+五查看器+五快捷键+大文件闸+删除态)按 SPEC 模板立,R/V 指针化,决策 D1–D8,PDF 明确划给 Phase 5。
- 新依赖预告:markdown-it(+task-lists)、CodeMirror 6(npmmirror 可取);Rust 新命令 read_text_file/read_media_file 复用 Phase 2 流水线。

### 2026-10-01 · 二轮反馈:拖到最顶修复 + 测试零前台立规

> **下一步从哪接** —— owner 复验(重点:置顶项**甩到最顶**和**拖到最底**)→ 过则 Done、进 Phase 3(先立 spec-003)。

- "拖不到最顶"根因两层:第一行上方约 30px 空白带(路径框+间隙)不接 drop;WebView2 要求 **dragenter 也 preventDefault** 才发 drop(lessons L10 补记)。修复=置顶行上/下半分插前/插后(顺带能拖到最底)+ 面板顶部区接"甩到顶"+ 行/面板双挂 dragenter/dragover。
- 验证改 **Playwright connect_over_cdp**(pywork):输入走 CDP 管道,应用 SW_SHOWMINNOACTIVE 最小化不激活,三场景(甩顶/最底/行内)全 PASS——**测试脚本从此禁止抢 owner 前台**(owner 立规,testing.md §1 已记)。
- V1.5 §197 审计加行(§39 落点语义细化);spec-002 D11;release 已重建。

### 2026-10-01 · Phase 2 验收反馈返工:排序合一/真拖拽修复/⋯并入 Settings

> **下一步从哪接** —— owner 复验(30 秒路径 testing.md §2b"验收反馈返工")→ 过则 Done、进 Phase 3(先立 spec-003)。

- owner 三条全落地:① 排序合一(Pinned 区+Unpinned 区单一排序制,V1.5 §33 增量修订+§197 审计);② 拖拽根因 = Tauri Windows 默认 `dragDropEnabled` 劫持 HTML5 DnD,配置置 false,**真实鼠标**(mouse_event)实测换序成功——CDP 合成 DragEvent 曾假阳性(lessons L10);③ ⋯ 菜单删除,Folders First/Show system folders/Refresh 住进 Settings 的 File Tree 区,⚙ 点进再点回 Files。
- vitest 重写 10/10、svelte-check 0/0;V1.5 §30/§33 增量修订+§197 审计表;release 已重建(桌面快捷方式自动最新)。
- owner 两问已答(收在会话汇报):Folders First 不勾=非置顶区文件文件夹混排按名;Refresh=重读已展开层并做 Pin 对账(实时监听是 Phase 9)。

### 2026-10-01 · Phase 2 交付:文件树/收藏/文件识别,自测全绿等验收

> **下一步从哪接** —— owner 验收(testing.md §2b 末尾)→ 通过后立 spec-003(Phase 3 Basic READ)。

- 六块全落地:Rust `list_directory`(单层+§29 打标)/`inspect_file`(§101 流水线,encoding_rs)→ 前端 fileTreeStore(相对路径身份)+treeSort 纯函数 → FileTree/TreeItem 懒加载树 + §30 ⋯菜单 + Pin 右键 + 同父拖拽 + Refresh rename 对账(1:1 才算可靠识别)。
- 自测:cargo 32/32(新增 24)、vitest 9/9(新引入)、svelte-check 0/0、CDP 全链(懒加载/可见性/两种排序/Pin 混排/拖拽/rename 保位/delete 清 Pin/磁盘 md5 前后对比 PASS);fixture `aiv-test-projects\TreeAlpha`(含 GB18030/二进制/5MB/21MB,用后可删)。
- release 已重建,桌面快捷方式自动最新;spec-002 增补 D9(树默认偏好 Name+Folders First,§17 未定取 VS Code 惯例)。
- 拖拽手感与 ⋯ 菜单视觉留 owner 手测;inspect_file 的 UI 消费(编码状态栏/Large File 确认框)按计划随 Phase 3 第一个 Viewer。

### 2026-10-01 · specs 体系对齐指南;owner 拍板 Spec 免审

> **下一步从哪接** —— 直接按 specs/spec-002 开工(六块提交切分),**不用再等 owner 点头**;动笔前有疑问/要变化先确认(workflow §五 A2)。

- owner 拍板三件:① **Spec 免审**("我就不过目了,你自己能跟原始需求对上就行"),替代门 = agent 自核 R/V 对齐 V1.5 + 疑问先确认;② **specs 体系按指南落**:仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机;③ 质疑指南是否有大问题——对证结论:**三件事指南全有明文**(00-doc-map 阶段2 行 11–12、阶段3 行 13、02-dev-workflow §二),错在 agent 立结构时未查指南、自创 docs/specs/phase-N(lessons L9)。
- 现结构:specs/{INDEX.md, SPEC-template.md, spec-001(Phase 1 追溯建档,Done), spec-002(Ready)};docs/workflow.md 含本项目适配 A1–A5(一段=一个 Phase、免审门、界面确认以 V1.5 为基线、V1.5 兼任 spec/roadmap、R/V 指针化)。
- 给 owner 的建议(改不改他定):指南可补一小节"项目已有权威需求基线(如本项目 V1.5)时怎么接入 specs/ 体系"——本项目接法可直接参考 docs/workflow.md §五。
- **修改建议已成文**:[docs/AI-Project-Guide-revision-proposal.md](AI-Project-Guide-revision-proposal.md)(3 条建议:基线项目特殊入场、建新结构先对号的路由行、SPEC 文件名唯一格式;每条带插入锚点+可粘贴草稿+验证用例)——owner 将交给改指南的 agent 执行;指南改定后需重拷同步仓内快照(建议文末有命令)。
- spec-001 已应 owner 要求补全为完整 SPEC 形态(R10 条/V6 组/实现方案/测试矩阵/验收原话,2026-10-01);AGENTS 路由表同步加"建新结构先对号"一行(lessons L9 的结构性修法)。

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

- **~~不另建 spec.md / roadmap.md / specs/~~**(2026-10-01 改口,出处:owner"每一段开发都要专门写一个 Spec 文档再开发";
  同日二次收紧:specs 按指南落仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机):
  现规矩 = **每个 Phase 开工前按 docs/workflow.md 状态机立 SPEC(根目录 `specs/spec-NNN`,编号与 Phase 对齐)**。
  spec-002 起执行,spec-001 追溯建档。原取舍(V1.5 兼任 spec/roadmap、待痛点出现再建)低估了"动代码前要有可审的实现方案与状态台账"这一痛点;
  V1.5 仍兼任产品规格与 roadmap(需求真值),specs/ 装实现方案与状态,两层用指针互指不抄正文。
- **需求变更走增量修订 + 变更审计(V1.5 §193),禁止整篇重写**:V1.2→V1.3→V1.4 三次整篇重写
  每次都丢过已确认规格,V1.5 起改为"只改明确条目+审计清单"后未再发生回归。

## 三、挂账区:等 owner 的事 + 非 SPEC 零散待办(一行一件,带去处)

> 债务表(debts.md)未建的阶段,这里就是**全部待办的家**;待办散落/约超 10 条 → 该建 debts.md。

| 事 | 去处(归谁·什么时候) | 提出日期 |
|---|---|---|
| 建异地备份 remote(私有库,SSH 认证),建好当天首推+核 0;建立之前仓库只有本地一份 | owner 亲手(方法:仓内 docs/AI-Project-Guide/07-backup-secrets.md)·**V1 全部完成后、owner 验收时**(2026-10-01 owner 拍板改期,不着急) | 2026-10-01 |
| V1.5 §196 附注 A(git -C 统一执行基准)合入 §65 正文 | agent·Phase 7 前 | 2026-10-01 |
| Playwright 回归脚本正式化入库(pywork 环境跑,替代 %TEMP% 手搓脚本;方案已口头验证可行) | agent·**等 owner 点头**(Phase 1 验收时顺带定;点头后约 30 分钟) | 2026-10-01 |
