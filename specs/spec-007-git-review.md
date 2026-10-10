# SPEC-007-GitReview —— 侧栏 Git:改了什么、跟远端差多少,一眼看完(只看不改)

> 状态:Ready(跃迁记录见 INDEX.md 那一行,本页不抄第二份)
> 创建:2026-10-10;Pre-Draft 结论出处 = V1.5 §181(Phase 7 清单)+ §8–§11/§20/§43–§78(git 域规格)+
> §152/§153/§174/§188 Git 各验收块;owner 放行开工(2026-10-10 原话"收口吧,我准备开新对话,做下一个需求",
> handoff 主线移交 Phase 7)。
> 本 Phase 免审依据 docs/workflow.md §五 A2(动笔前疑问清单:无阻塞项;V1.5 未含明文的界面细节由决策表代取默认+标"未确认")。

## 〇、值不值得做

- 好处:owner 的核心工作流就是"看 agent 改了什么"——现在必须切去 VS Code 或敲命令行;Git 面板把 M/A/D 文件、Diff、近期提交收进侧栏,每次查看省一次上下文切换(§43:熟悉 VS Code 的用户零学习成本)。
- 代价:一个开发段(Rust git.rs 两命令+解析器 ~600 行、前端 gitStore+GitPanel+DiffViewer、树/徽标/页签三处挂点);可能碰坏的=文件树行渲染(标记列)、侧栏头部(徽标)、↻ Refresh 语义(0.6.5/0.6.6 两轮 owner 亲自打回的交互,回归须带上)。
- 判:值→做(V1.5 §181 明列 Phase 7)。

## 一、Pre-Draft 结论

- 核心选择题:无新增(V1.5 已写死:信息架构=VS Code Source Control §43–§46;只读不改 §45;系统 git CLI §68;
  porcelain=v2 --branch §69;安全旗标 §70;统一 `git -C <GitRoot>` §65(2026-10-10 附注 A 已合入正文);
  Diff 尺寸守卫 §72;刷新四触发 §73)。
- 标杆对照:VS Code Source Control View(保留 Badge/Branch/Ahead-Behind/Changes/Staged/点文件看 Diff/Recent Commits,
  删除全部 Mutation §44/§45)。
- **界面确认**:§8/§9/§50 面板明文 = 已确认基线(workflow §五 A3);未含明文的细节(标记配色/clean 态文案/
  untracked 点击行为等)由决策表代取默认+标"未确认"。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

| R# | 需求(使用者视角;真值 = V1.5 节号) |
|---|---|
| R1 | 每个 Project 打开/刷新时先探明 Git 身份:Project Root = Git Root → 正常仓库视图(§56);Project Root 在更大仓库内部 → 子目录模式,面板顶部显示 Repository 名 + Scope 路径,Badge/Changes/树标记只算 Scope 内,Branch/Ahead-Behind 仍是仓库级(§57–§64);不属于任何仓库 → 面板显示 "This folder is not a Git repository.",不阻塞项目打开(§152/§66);git.exe 不存在 → "Git is not installed or cannot be found." + "File browsing remains available.",不阻塞应用(§153) |
| R2 | 侧栏头部 Git 按钮带 Badge `Git [7]`:当前 Project Scope 内变化的唯一文件路径数;同文件 Staged+Unstaged 只计一次;0 → 不显示;≥100 → `99+`(§8/§9/§53);非 Git 项目/git 缺失不显示 |
| R3 | 项目标签显示 ✓(Scope 内无变化)/ ●(有变化),不带数字;非 Git 项目不显示符号(§10/§46/§60) |
| R4 | Git 面板按 §50 结构:顶部 `main ↑2 ↓1`(无 Upstream 则无 ↑↓,§67;子目录模式加 Repository/Scope 两行 §58);CHANGES 组=未 Stage 的变化+未跟踪文件(§51/§50 例含 `? notes.md`);STAGED CHANGES 组=已进 Index 的变化(§52);同文件允许两组同现不去重(§53);点击 CHANGES 行 → 主区打开 Working Tree Diff,点击 STAGED 行 → Staged Diff(§51/§52);RECENT COMMITS 默认 20 条=Short Hash+Message+相对时间(如 2h ago / yesterday),子目录模式只显示影响 Scope 的提交(§54/§64) |
| R5 | 文件树文件行显示 Git 字母标记 M/A/D/R/?/U,仅文件、文件夹不聚合不显示(§46/§47/§48);折叠目录的隐藏变化是有意取舍,完整变化看 Badge(§49);子目录模式只标 Scope 能映射到的文件(§62) |
| R6 | Diff 用 Unified 格式(Working Tree/Staged 两类,§71);超限(2MB 或 20000 行,后端截断)→ 显示 "Diff is too large to display." + [Open in VS Code] 按钮(§72) |
| R7 | 后端安全命令层:只用系统 git CLI,argv 硬编码不拼 shell(§68);状态解析 porcelain=v2 --branch(§69);统一 `git -C <GitRoot>` 执行、输出统一相对 Git Root 再换算 Scope(§65);Diff 带 --no-pager / core.quotepath=false / --no-ext-diff / --no-textconv(§70,中文文件名正常) |
| R8 | 刷新触发=Project Open / Project Switch / Window Focus / Manual Refresh(§73,Phase 9 watcher 不在本期);Git 状态是 Runtime 态,永不持久化,重启重读(§20);防抖约 400ms(§75) |

**反例规则(不许做什么)**:不做任何 Git Mutation——Stage/Unstage/Commit/Discard/Push/Pull/Sync/Branch/Merge/Rebase 全部不出现(§45);前端不获得任意命令执行能力,git 只在 Rust 侧以固定 argv 调用(§133 同族纪律);无高频轮询(§188 Performance:无高频 Git Poll)。

## 三、验证标准(V 编号;组级指向 §188 Git 各块)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1/R7 | cargo(临时真仓库):子目录项目 rev-parse 得父仓 Root+scope 计算;porcelain=v2 解析出 branch/upstream/ahead/behind 与 M/A/D/R/?/U 全字母;renamed 双路径都解析;空仓库 commits=[];detached HEAD 不炸 | 自动 |
| V2 | R1/R4 | cargo(§174 场景仓):Scope=apps/viewer 时 Badge 数只含 viewer 内 unique 路径;backend/packages 的变化不进 changes/staged;log 带 Scope pathspec 后只返回影响 viewer 的提交;branch/ahead-behind 与 Scope 无关 | 自动 |
| V3 | R6/R7 | cargo:diff argv 含四个安全旗标;30000 行变更的 diff 返回 truncated=true 且行数≤20000、字节≤2MB | 自动 |
| V4 | R2/R4/R5 | vitest 纯函数:relativeTime(now-ts) 各档(just now/Nm/Nh/yesterday/Nd);badgeText(0)=null / (7)="7" / (100)="99+";treeMark 同文件 staged 优先 | 自动 |
| V5 | R1–R5 | phase3(git 夹具 §174 三实例):BigRepo 根=正常模式(badge=全仓 unique 数、面板无 Repository/Scope 行);BigRepo\apps\viewer=子目录模式(§174 七勾:badge 只 viewer/● 只 viewer/Changes 只 viewer/树只标 viewer/Branch 仓库级/Commits 只 viewer/显示 Repository+Scope);AIV-TestProject=非 Git(面板文案 §152、无 badge、标签无符号) | 自动 |
| V6 | R4/R6 | phase3:点 CHANGES 行 → 主区出现 diff 视图含 `+`/`-` 行与文件名;点 STAGED 行 → 同一文件另一版本 diff;未跟踪行 → 打开文件内容视图;关闭按钮/点文件页签 → 回到原查看器 | 自动 |
| V7 | R2/R4 | phase3:同文件先 stage 再改 → 两组各有一条、badge 只计一次(§53) | 自动 |
| V8 | R4/R6 | phase3:构造超限 diff(夹具生成大改文件)→ 显示 "Diff is too large to display." + Open in VS Code 按钮,UI 不冻结 | 自动 |
| V9 | R8 | phase3:磁盘上改一个文件 → 点 ↻ → badge 数字与树标记即时变化(Manual Refresh 实证;Project Open 随实例启动自带;Switch/Focus 触发为 onMount 接线+代码审查口径,owner 真机顺手验) | 自动+人工(部分) |
| V10 | R5 | phase3:树中 M/A/D/R/? 文件行各有对应字母且文件夹行无标记;标记随 ↻ 刷新同步消失(文件 revert 后) | 自动 |

> V-human 占比:V9 半条(Switch/Focus 留 owner),自动 10 条 ✓。§188 Git Availability 4 勾=V5;Git Subdirectory Scope 12 勾=V2+V5;Git UI 9 勾=V4+V5+V7;Git Status 13 勾=V1+V7;Git Diff 11 勾=V3+V6+V8;Recent Commits 5 勾=V1+V2+V5;Watcher 块=Phase 9 不在本期。

## 四、技术实现方案

- **Rust 新模块 `src-tauri/src/git.rs`**(模式随 handoff.rs:语义命令+canonicalize 校验+单测):
  - `git_snapshot(root) -> GitSnapshot`:①`git -C <root> rev-parse --show-toplevel`(spawn NotFound→gitMissing;exit≠0→nonGit);
    ②canonicalize 双方算 scope(相对 Git Root 正斜杠);③`git -C <GitRoot> status --porcelain=v2 --branch` 解析
    (branch.head/upstream/ab;1/2/u/? 行;renamed 双路径);④`git -C <GitRoot> log -n 20 --pretty=%h␟%s␟%ct [-- scope]`(空仓库→[])。
    Scope 过滤+Project-relative 换算在 Rust 侧完成,前端只见项目相对路径(§65)。
  - `git_diff(root, rel, staged) -> {text, truncated, lines}`:rel 先过 resolve 校验(§143/§144 同款),换算 Git-Root-relative;
    流式读 stdout,**字节 2MB / 行 20000 双顶**任一触顶即 kill 子进程置 truncated(§72,内存有界)。
  - 解析器抽纯函数 `parse_status_output(&str, scope)` 便于喂手写夹具;进程层统一超时 10s(挂死防护),argv 全常量+校验后路径,
    无 shell 无拼接(§70/§133)。冲突(u 行)进两组各标 U(badge 仍计一次)。
- **前端 `stores/gitStore.svelte.ts`**:每项目 RuntimeGitState(§20 接口,零持久化);`refreshGit(root)` 400ms 防抖(§75)+
  in-flight promise(↻ 动画等它);接线:onMount 启动扫全项目(页签指示要)+新增项目补扫、activeProject 变化(Open/Switch)、
  `getCurrentWindow().onFocusChanged`(Focus,只刷激活项目 §78);`forgetGit` 挂 removeProject 旁(forgetTree/forgetTabs 同点)。
- **`gitFormat.ts` 纯函数**(vitest 可测):relativeTime/badgeText/treeMark;types 放 tauri.ts(GitSnapshot/GitChangeEntry/GitCommit)。
- **组件**:GitPanel 重写(§50 结构+三空态 §152/§153/clean+行点击);SidebarHeader Git 按钮挂 badge;ProjectTabs 挂 ✓/●;
  TreeItem 文件行挂字母标记(仅文件行);**DiffViewer.svelte**=查看器区单槽 diff 视图(gitStore.activeDiff;±/@ 行着色,
  头部文件名+Working Tree|Staged+关闭;超限时换 "Diff is too large…" + Open in VS Code 复用 handoff 命令)。
- **刷新联动**:App.svelte 的 ↻ onRefresh 改 `Promise.all([refreshProject, refreshGit])`(0.6.6 旋转动画自然覆盖两件事);
  Ctrl+R 同步加 git 刷新(§73 manual 手势族)。
- **版本 0.6.7**(三处),发布前核段号(D12;L23)。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | snapshot/diff 两命令,不设独立 summary 命令 | snapshot 本身轻(≤3 次 spawn,实测 git status 毫秒级);§78 的 inactive 低成本 summary 在 Phase 7 无触发场景(切过来即全量刷新) | git_summary 轻量命令 | YAGNI,两套返回形必漂 |
| D2 | untracked 行点击=打开文件内容视图,不合成 new-file diff | §51 只约束 CHANGES 点击打开 Working Tree Diff;untracked 无 diff 可言,VS Code 旧版即打开内容;合成 diff 需读文件+造 hunk(额外路径+内存) | 合成全绿 new-file diff | 回退条件:owner 要"新增文件全绿 diff"再加 |
| D3 | Diff=查看器区**单槽视图**,不入文件页签 | 内存第一原则(单份 ≤2MB 缓冲,关闭/切换即释放,多页签=N 份);页签身份是 relativePath(树高亮/持久化/Ctrl+W 共用),塞 diff 伪身份必污染四处;§51"主 Viewer 打开"单槽已满足 | diff 作为第 7 种 ViewerType 页签 | 上述身份污染;回退条件:owner 要 diff 可固定/多开 |
| D4 | 树标记字母:staged(X)优先于 worktree(Y) | 同文件两组并存时只显一个字母;index 状态是"将提交的",语义更强;**未确认**(V1.5 无明文,VS Code 亦无单字母明文) | worktree 优先 | 随手改即翻案,决策表行即回退点 |
| D5 | 标记配色 M 琥珀/A 绿/D 红/R 蓝/? 灰/U 紫,双主题各配 | VS Code 惯例色系;**未确认**(V1.5 无配色明文) | 单色 | 五字母单色失去扫读价值 |
| D6 | clean 仓库面板=branch 行+commits,CHANGES 区显示 "No changes." | 空态要有落点;**未确认** | 完全空白 | 用户分不清"没变化"与"没读到" |
| D7 | detached HEAD 显示 branch.head 原文("(detached)"),无 upstream/ab | porcelain=v2 原样;V1.5 无明文 | 隐藏 branch 行 | 丢信息 |
| D8 | 空仓库(无提交)commits=[],不算错误 | git log exit 128+特定 stderr=正常业务态 | 当 error 冒泡 | 面板会吓用户 |
| D9 | git 进程 10s 超时,超时 kill→snapshot status=error(面板显示错误文案) | 巨仓/网络盘可能挂死;防 UI 永久等待;无轮询不会堆积 | 无超时 | 挂死进程+悬挂 promise |
| D10 | 启动时顺序刷新全部项目(页签 ✓/● 需要),激活项目优先 | §46 第一层要求每项目指示;§20 禁持久化→启动必须重读;顺序=无 spawn 风暴;§78 inactive 不维持实时(Phase 9 才有 watch) | 只刷激活项目 | 页签指示退化成"当前项目才有" |
| D11 | 冲突文件(u 行)进两组各标 U | V1.5 只有两组无 Merge 组;两组并存最接近"index 与 worktree 都有变化"事实;badge 计一次不受影响 | 单独第三组 | §50 无此结构 |
| D12 | 版本 0.6.7(三处) | owner 2026-10-10 立规 0.6.x 固定递增不跳段(D7 于 INFRA-003);L23 段号纪律 | 0.7.0 | 明令不跳段 |
| D13 | ↻ 与 Ctrl+R 都连带 git 刷新 | §73 Manual Refresh 两个可见入口都算;Promise.all 让 0.6.6 旋转动画如实覆盖全部工作 | 只刷树 | 两入口状态走岔必挨报障 |
| D14 | Focus 只刷激活项目 | §78 字面 | focus 刷全项目 | 多项目 spawn 放大,owner 无感 |

**内存账**:gitStore 每项目一份快照(文件条目+20 提交,纯数据,移除项目即 forget;不落盘);DiffViewer 单份 diff 文本 ≤2MB,
关闭/切项目/刷新后文件不再变化时即释放;无轮询定时器,防抖 timer 触发即消;Rust 侧 diff 流式截断,大 diff 永不整块进内存。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1/R7 | V1 | cargo:临时真仓库(init/commit/mv/冲突/clone 出 upstream)+手写 porcelain 夹具喂纯解析器 | cargo 临时目录(测试内自建 git 仓) | ✓ |
| R1/R4 | V2 | cargo:§174 场景仓断言 scope 过滤/unique/log pathspec/branch 仓库级 | 同上 | ✓ |
| R6/R7 | V3 | cargo:安全旗标 argv 断言+大 diff 截断 | 同上 | ✓ |
| R2/R4/R5 | V4 | vitest:relativeTime/badgeText/treeMark | 无 | ✓ |
| R1–R5 | V5 | phase3:BigRepo 根(正常)/apps/viewer(子目录)/AIV-TestProject(非 Git)三实例 | %TEMP%\aiv-p7-gitscope(套件内生成器自建 git 仓) | ✓ |
| R4/R6 | V6 | phase3:三点击路径+关闭回原查看器 | 同上 | ✓ |
| R2/R4 | V7 | phase3:同文件双组+badge 单计 | 同上 | ✓ |
| R6 | V8 | phase3:超限 diff 文案+按钮 | 同上(生成大改文件) | ✓ |
| R8 | V9 | phase3:改盘→↻→badge/标记变化;Switch/Focus 接线代码审查+owner 真机 | 同上 | ✓(部分 owner) |
| R5 | V10 | phase3:字母与文件夹无标记+随刷新消失 | 同上 | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物(矩阵/自检/验收原话) |
|---|---|---|
| 2026-10-10 | 立项 Draft→Ready(免审,workflow §五 A2:R/V 与 V1.5 §181/§43–§78/§152/§153/§174/§188 逐条对上,决策表 D1–D14 齐,无疑问需确认) | 测试覆盖矩阵 10 条 |
