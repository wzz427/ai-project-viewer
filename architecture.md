# architecture —— AI Project Viewer 技术架构(怎么做)

> 记录技术选型与实现结构。需求与开发顺序见《AI Project Viewer 产品需求与技术设计文档 V1.5 FINAL.md》
> (唯一基线,兼任 spec),交接见 docs/handoff.md,测试规范见 docs/testing.md(未建)。
> **§0 开发环境是建仓第一天就填实的**,其余随项目长。

## 0. 开发环境与跑法(新 agent 第一站;判据:只读这节就能把项目跑起来)

| 项 | 值 |
|---|---|
| 解释器 / 运行时 | 前端 Node v24.14.0(npm 11.9.0 / pnpm 11.1.3);Rust rustc/cargo 1.98.1 stable(x86_64-pc-windows-msvc,rustup 用户级安装于 `%USERPROFILE%\.cargo`;MSVC 链接器由已有 VS 2022 Build Tools 提供,hello-world 编译运行已验证)。⚠️ 安装后仅新终端 PATH 含 cargo,已开着的会话需 `export PATH="$USERPROFILE/.cargo/bin:$PATH"`。**测试/脚本用 Python:conda 环境 pywork**(`C:\Users\wzzpk\.conda\envs\pywork\python.exe`,Python 3.12.13,Playwright 已装;conda 本体 `C:\ProgramData\miniconda3` 不在 PATH,直接用全路径调 python.exe 即可)——owner 指定,别用系统 Python |
| 包管理 | pnpm(前端,**仓库 `.npmrc` 固定 npmmirror 镜像**,npmjs 直连不通)+ cargo(crates.io 直连可通);Windows 11 + WebView2 Runtime 143 |
| 装依赖 | `pnpm install`(前端);Rust 依赖随首次构建自动拉取,`cd src-tauri && cargo fetch` 可预取 |
| 启动(开发) | `pnpm tauri dev`(起 Vite:1420 + debug exe);要可独立运行的 debug exe:`pnpm tauri build --debug --no-bundle` → `src-tauri/target/debug/ai-project-viewer.exe` |
| **打正式安装包** | `pnpm tauri build`(owner 点头才打,红线)→ `src-tauri\target\release\bundle\nsis\AI Project Viewer_<版本>_x64-setup.exe`;**离线大包** ~210MB(webviewInstallMode=offlineInstaller,owner 2026-10-26 拍板,对方电脑缺 WebView2 也能装);未签名→他人首装弹 SmartScreen 蓝警告属预期;正式版无 CDP 端口/无更新渠道(纯本地目录机制,别人电脑上天然不动作);**重发新版=重新打一个 setup.exe 给对方**(V1 决定:正式版不带自动更新) |
| 跑测试 | 见 docs/testing.md §1(唯一真值):`pnpm check` / `cd src-tauri && cargo test` / 构建;Benchmark 档位见 V1.5 §162–§173 |
| 调试端口(CDP) | dev/体验版**常开** 9322:lib.rs 启动时若 env 未设则给 WebView2 加 `--remote-debugging-port=9322`(e2e 自设端口优先);活体直连=`scripts/e2e/live-inspect.py` 只读快照(owner 2026-10-12 指令,现场报障第一动作)。**正式安装版已关(2026-10-26,spec-011 债清偿)**:门禁按渠道标识——`.exp`(体验版)与 debug 构建(=tauri dev)保留端口;默认标识+release(=NSIS 正式版)**永不设端口**(lib.rs `merge_webview_args` 纯函数+6 单测;正式版启动实证全进程树零监听)。`--disable-direct-composition`(黑线案)全渠道保留 |
| 🔒 备份(异地) | **remote `backup` = `git@github.com:wzz427/ai-project-viewer.git`**(SSH;owner 给的 https 直连在此网络被重置,且指南铁律=远程必须 SSH 地址)。认证=`~/.ssh/github_wzz` 账号级钥匙(一钥匙管一事,与 Gitee/服务器不共用;`ssh -T git@github.com` 回 `Hi wzz427!` 为通)。方法全文=docs/AI-Project-Guide/07-backup-secrets.md + Desktop 指南 advanced/02(两平台篇)。**本项目备份规则**(2026-10-12 立,细则见下方「备份规则」块) |
| 平台已知坑 | ① 路径含空格/中文必须加引号;② WebView2 浏览器加速键抢占应用快捷键 → 已在 Rust 侧 COM 禁用(§147,src-tauri/src/lib.rs);③ git 输出路径基准不一致:status 相对 cwd、diff/log 相对 Git Root,一律用 `git -C <GitRoot>` 规避(V1.5 §196 附注A);④ Rust `canonicalize` 产生 `\\?\` 前缀 → 用 dunce crate(V1.5 §144);⑤ 无 BOM UTF-8 的 .ps1 含中文会被 PS5.1 按 GBK 误读导致解析错乱(lessons L2) |
| 🚫 别碰 | 需求文档是唯一基线,不得未经 owner 修改;密钥文件别读(见 AGENTS.md 红线);不得绕过 V1.5 §143–§147 安全章节"图快" |

### 备份规则(2026-10-12 owner 指令建线,agent 依指南 advanced/02 拟定)

1. **节奏**:一段工作收尾(commit 之后)就推 `git push --force backup main --tags`——AGENTS §五既有规矩,与 commit 同性质,不攒批。**没 commit 的改动不在备份里**(当前 docs/AI-Project-Guide/ 另一会话未提交改动即不在内,该会话收口自会入账)。
2. **核账**:推完必核 `git rev-list --count backup/main..main` = `0`;只信退出码不够。git banner 走 stderr——红字≠失败,以退出码+核账数为准(指南实测坑)。
3. **`--force` 语义**:备份库只有本机往里推,force=远端完全等于本地 main,不存在覆盖他人;远程若意外变 https 地址,先 `git remote set-url backup git@github.com:...` 纠正再推。
4. **装不下(红线)**:密钥(`.env*`/`*.key`/`*.pem`/`secrets/`,.gitignore 占位+推前历史扫描);可重建大物(node_modules/target*/dist);推备份的钥匙本身(只在 `~/.ssh/`);体验渠道二进制(updates/ 在 LOCALAPPDATA,本就不在仓)。
5. **恢复**:本地全丢 → 新机 `git clone git@github.com:wzz427/ai-project-viewer.git`(clone 不需要那把推送钥匙,网页登录即可;此网络 https 直连不稳,SSH 稳)→ 密钥单独放回 → 重装依赖。
6. **演练**:每季度或发大版后,`git clone` 到 `%TEMP%\backup-drill` 对一眼 HEAD 再删——真拉一次才算验证过。
7. **第二平台**:现只挂 GitHub 一线;要加 Gitee 主备份时按指南另挂 remote(两远端各自单独推,互不替代)。
8. **可见性**:该库应为 **Private**——owner 建库时网页上确认一眼(agent 无法读取可见性,记为 owner 确认项)。

## 1. 核心决策表(D 编号;否决项一栏是灵魂——三个月后有人问"为什么不用 X",答案住这)

> 全部决策的完整论证见 V1.5 对应章节;本表是落地索引。

| # | 决策项 | 选定方案 | 否决项 / 关键理由 | 出处 |
|---|---|---|---|---|
| D1 | 桌面框架 | Tauri 2 + WebView2 | 否决 Electron:低 RAM 是核心目标,不为生态引入完整 Chromium | V1.5 §156/§163 |
| D2 | PDF 方案 | PDF.js(含虚拟化/懒加载/非活动释放) | 否决 WebView2 Native PDF:宿主无法控制工具栏/页码/搜索/生命周期,是能力缺失不是性能差异 | V1.5 §91–§98 |
| D3 | 代码查看 | CodeMirror 6 Minimal Read-only | 否决 Monaco:携带大量 IDE 能力,违背 Viewer-only | V1.5 §107 |
| D4 | Markdown | markdown-it,Raw HTML 默认禁用 | 禁脚本执行的安全要求 | V1.5 §86–§88 |
| D5 | Git | System git CLI,只读 Review,全部 `git -C <GitRoot>` + 安全参数(`--no-pager`/`core.quotepath=false`/`--no-ext-diff`/`--no-textconv`) | 否决内嵌 git 引擎:维护成本;安全参数防仓库配置触发外部程序 | V1.5 §68–§70/§196A |
| D6 | 状态持久化 | JSON + debounce 500–1500ms + 原子替换,AppState.version=1 + migration 骨架 | 否决 SQLite:状态量小不值当 | V1.5 §23–§26 |
| D7 | 文件树排序 | Name + Favorites First(Pinned 手工序 + Unpinned 自动序) | 否决 Full Manual Sort:Agent 高频增删文件,人工顺序维护成本持续上升 | V1.5 §33–§40 |
| D8 | Git 子目录场景 | Git identity 仓库级、变化呈现项目级(Badge/Changes/Tab 只算 Project Scope,Branch/Ahead/Behind 仓库级) | 否决父仓库全量呈现:与"当前项目"直觉不符;否决 multi-repo 递归发现:复杂度 | V1.5 §55–§66 |
| D9 | UI 布局 | Sidebar Header Tabs(Files/Git),非 Activity Bar | 否决竖向 Activity Bar:两个工作区不值得占一列 | V1.5 §7–§8 |
| D10 | opener 插件授权(渲染层) | capabilities 只授 `opener:allow-open-url`(http/https);**不授 open-path/reveal/mailto** | 否决 `allow-open-path **`:渲染层处理不可信 PDF/代码文件(pdf.js/CM 为现实攻击面),曾授权任意路径 OS 关联打开=可执行程序;插件文档证实 scope 仅 IPC 层强制,Rust 自由函数(open_path/reveal)不受影响——收紧零代价(spec-011 R20/phase3 双拒探针) | spec-011 §四 D8;2026-10-11 |
| D11 | cmd.exe 宿主传脚本路径 | `raw_arg` 双层引号 `""path""`(SpawnArg::CmdPath) | 否决裸 argv/单层引号:cmd 的 /K 文档行为=引号内含元字符即剥外层引号重析,单层引号下 `a&calc&` 文件夹实证跑出 calc(§145) | spec-011 §四 D7;2026-10-11 |
| D12 | 前端工作区生命周期 | 每项目 viewer 区按 rootPath `{#key}` 整体重挂载(App.svelte);`projectTabs()` 创建分支返回 store 代理而非裸局部对象 | 否决"逐点修补订阅失效":ActiveViewer 的 `$derived(activeTab)` 与 tabsState 失联且跨项目蔓延(0.7.12 冻结大案,诊断 #3 MISMATCH 行+机理定位);keyed 重挂=订阅不可能跨项目变陈;本地复现率仅 ~2%,统计证不出但机理修(L43) | 0.7.12 冻结案;docs/testing.md §4 |
| D13 | 常开探查端口 | lib.rs 启动时(env 未设则)给 WebView2 加 CDP `--remote-debugging-port=9322`;配合 `__aiv.snapshot()`(debugHook.ts)供 live-inspect.py 只读直连 | 否决"只靠诊断日志复盘":owner 指令——软件就在本地开着,应当能直接取现场信息;只读不控、不启不杀;**正式安装版已关(2026-10-26):门禁=渠道标识(.exp/debug 保留,默认标识+release 永不设),见 §0 调试端口行** | owner 2026-10-12 指令 |
| D14 | UI 皮肤体系(spec-014) | app.css 单文件 tokens:三档字阶 11/12/13(600 字重做层级,唯一例外=EmptyState hero 20px)+语义色(--danger 唯一错误红/--accent-soft 染色层/--accent-strong 实底专用)+暗色三面阶梯(壳/阅读面/浮层)+Icon.svelte 内联 SVG 单表(16 枚,2px 描边 24 网格,currentColor)+项目首字徽标 hash(rootPath)→8 色板稳定身份+文件类型图标族复用 viewerType 路由 | 否决图标库/五档字阶/随机徽标色/实底徽标:零依赖+内存最小化+颜色身份可学习+quiet 基调(论据全表=specs/spec-014 §四 D1–D8);对比度全数值化实测(WCAG AA) | owner 2026-10-12 拍板(A 方案/一步到位/亮色为主);评审快照 .impeccable/critique/2026-10-12T09-25-27Z |

## 1.5 待决问题(摆上桌但"以后再说"的;不是 bug 不是待办,是没被遗忘也没被拍死的取舍)

| # | 问题 | 已知事实 | 何时回来评估 | 归档日 |
|---|---|---|---|---|
| ~~Q1~~ | ~~发布形态(安装包格式/签名/自动更新)~~ | **已拍板(2026-10-11,owner"开工"确认 §184 初始建议):NSIS Setup EXE / V1 不签名 / V1 关自动更新**;V1.5 §197 审计行;实际打包发布=独立动作走红线闸 | 公开分发时重评 Code Signing/Updater/MSI(§184) | 2026-10-11 |
| Q2 | Multi-Repository Workspace(一个 Project 含多个嵌套 repo) | V1.5 §66 明确不做,视为 Non-Git | 真实使用出现该痛点后(V1.5 §187 Future) | |

## 2. 整体拓扑(一张图;Phase 1 实测核实)

```
┌──────────────────────────── AI Project Viewer 进程树(7 进程,Phase 1 实测)────────────┐
│  Rust 主进程 ai-project-viewer.exe(Private 5.9MB,src-tauri/)                          │
│   ├─ project/(Phase 1 已建:canonicalize/去重);fs/ git/ runner/ external/ security/   │
│   │  state/(Phase 4 已建:load/save_state+原子替换+迁移骨架+测试态闸门)               │
│   │  updater.rs(SPEC-INFRA-001:体验版更新——check/apply/relaunch+md5 流式+rename 自替换) │
│   ├─ 插件:single-instance(二次启动激活已有窗)/ dialog(文件夹选择、确认框)          │
│   └─ ↔ IPC(Tauri Commands:resolve_project / startup_elapsed_ms /                   │
│        list_directory / inspect_file / read_text_file / read_media_file /           │
│        load_state / save_state;清单见 V1.5 §159)                                     │
│        ↕ WebView2 ×6(browser/renderer/GPU/network/storage/crashpad,Private 合计~173MB)│
│  Svelte 5 前端(src/,纯 Vite 无路由,组件/ stores/ services/ 见 §3)                    │
│  外部(后续 Phase):System git.exe / PowerShell / CMD / 默认浏览器 / Explorer / VS Code │
└──────────────────────────────────────────────────────────────────────────────────────┘
内存统计口径 = 整个进程树(V1.5 §161);Baseline 数字见 docs/testing.md §3
```

## 3. 代码地图(目录一变就同步;过时的地图比没有还坑人)

> 还没写出来的条目标 **(规划)**;InDev 落地当天把(规划)改实——拖着不改,它就成了过时地图。

```
ProjectViewer/(仓库根)
├── AI Project Viewer 产品需求与技术设计文档 V1.5 FINAL.md —— 唯一需求基线(做什么+怎么做+Phase 计划+验收)
├── AGENTS.md —— agent 第一读物(灵魂+路由)
├── demand.txt —— owner 原始需求原话
├── architecture.md —— 本文件(环境跑法+决策表+地图)
├── specs/ —— SPEC 体系(开工前立项,INDEX.md 台账为状态唯一真值;workflow 状态机在 docs/workflow.md)
│   ├── spec-001-application-shell.md(Phase 1,Done)
│   ├── spec-002-file-system-and-favorites.md(Phase 2)
│   └── SPEC-template.md / INDEX.md
├── docs/
│   ├── handoff.md —— 交接页(现在在哪、上一段为什么)
│   ├── testing.md —— 测试档位+Baseline 真值
│   ├── how-to-report.md —— 汇报模板
│   ├── doc-maintenance.md —— 文档同步总表
│   ├── wrap-todo.md —— 一轮寿命执行清单(wrap 配套)
│   ├── workflow.md —— SPEC 状态机+跃迁自检门(本项目适配 A1–A5)
│   ├── AI-Project-Guide/ —— 指南仓内副本(2026-10-01 入库;test-run 未搬)
│   ├── AI-Project-Guide-revision-proposal.md —— 给指南的修改建议
│   ├── lessons.md —— 踩坑账
│   └── history/INDEX.md —— 历史归档入口
├── .zcode/commands/wrap.md —— /wrap 斜杠命令(压缩前收尾,方法全文)
├── index.html / vite.config.ts / tsconfig.json / svelte.config.js / package.json / .npmrc —— 前端工程(纯 Vite+Svelte5,无 SvelteKit)
├── scripts/install-experience.ps1(体验版一次性装机:独立目录+state 迁移+快捷方式)
├── scripts/publish-experience.ps1(每轮交付:构建 .exp 配置+放 updates+写 update.json——交付流程见 testing.md §2f)
├── scripts/e2e/ —— e2e/工装脚本集群(档位与跑法唯一真值=docs/testing.md §1/§3;⚠️ 零打扰红线:aivlaunch.py PID 限定启动,绝不按进程名杀/按标题找窗)
│   ├── 回归五套:phase3-suite / git-suite / recent-suite / acceptance-r3 / pdf-suite(夹具自建,make-fixtures/oracle 供)
│   ├── benchmark-suite.py —— T3 全量性能档(A–I+Baseline;🔴 owner 批准才跑,结果落 %TEMP%\aiv-bench)
│   ├── freeze-repro.py / freeze-probe.py —— 内容冻结复现器/探针(0.7.12 大案工装;probe 支持 FREEZE_PROBE_EXE/FAST)
│   ├── live-inspect.py —— 活体直连(CDP 9322 只读快照;不启不杀不聚焦;现场报障第一动作,D13)
│   └── visual-check-014.py —— spec-014 视觉自检(双主题 7 张截图,offscreen 显示窗口 CDP 出图;截图供人眼/视觉模型终审)
├── src-tauri/experience.conf.json(体验版构建片段:identifier .exp,数据/单实例与开发版全隔离)
├── public/favicon.png
├── src/ —— Svelte + TypeScript 前端
│   ├── main.ts / App.svelte / app.css(主题 tokens,data-theme 切换)
│   └── lib/
│       ├── components/ProjectTabs/(顶栏项目标签:增/删/切/active;**AddProjectMenu=0.7.3 + 号两段式菜单,V1.5 §198**:Browse 永第一项+Open Recent 列表悬停✕+Clear,空表时 + 仍直开选框)
│       ├── components/ContextMenu/(ProjectContextMenu:项目右键菜单,顶栏标签与 Files 面板路径共用)
│       ├── components/SidebarHeader/(Files/Git[徽标 §9]/⚙/↻)
│       ├── components/FileTree/(FileTree 宿主 / TreeItem 递归行 / NodeContextMenu Pin 右键)
│       ├── components/ProjectTabs/FileTabs.svelte(主区文件标签条)
│       ├── components/Viewers/(ActiveViewer 路由(**Phase 9:{#key}=rel+contentRev——外部重读后 CodeMirror/PDF 重挂载换内容,§160.5 保滚动**) / MarkdownViewer / **CodeViewer+codeLanguages+codeSearchRegistry(0.7.4:字号一变即重建编辑器实例——CSS 变量改字号 CM 看不见,缓存行高过期致行号列逐行漂移(owner 截图报障);行号随正文同字号)** / JsonViewer / ImageViewer / **PdfViewer(Phase 5:pdfjs legacy+工具栏+虚拟化+切离释放)** / **DiffViewer(Phase 7:side-by-side 并排 diff 单槽视图,0.6.8 返修:双栏行号+路径列头+红绿对置+空侧斜纹+折叠计数条,parseUnifiedDiff 纯解析(D16);§72 超限 Open in VS Code,Esc/× 关)** / **CommitDetailView(0.6.8 返修:提交详情单槽——Message/作者/日期/Hash/文件列表,文件点入提交视角 diff)** / UnsupportedViewer / **ViewerToolbar+activeFind(0.6:文本类统一操作栏=全局字号+Find;Ctrl+F 注册表)** / **ExecutableInfoViewer(Phase 8:§122 exe 信息卡=stat 纯字段,无内容缓冲)** / **ErrorDialog(0.6.13:窗口正中单槽错误弹窗=Run 失败醒目反馈,§119 修订;Esc/OK/背板关)**)
│       ├── components/SidebarPanels/(Files=路径框+FileTree / **Git=Phase 7 面板(§50 分支行↑↓/子目录 Repository+Scope 盒/CHANGES+STAGED+RECENT COMMITS/§152/§153 三空态)** / Settings)
│       ├── components/EmptyState/(首启空态,V1.5 §151 文案;0.7.3 §198-b:最近列表非空时 Open Folder 下方渲染只读 Recent 列表,点击即开,失效置灰)
│       ├── components/Toast/(单槽 toast)
│       ├── stores/projectStore.svelte.ts(项目列表+去重+增删+每项目 sidebarMode/Width;会话字段,持久化走 appState;addProjectFromPath 成功两分支(新加/切换)记 Open Recent,spec-010 D1:会话恢复不记)
│       ├── stores/settingsStore.svelte.ts(AppSettings:theme/fontSize/全局 showSystemFolders;Phase 4 起持久化)
│       ├── stores/diagnosticsStore.svelte.ts(启动耗时/拦截计数,给验收当证据;0.6.12 增 600 条运行日志环——全局 error/rejection+boot/tab/viewer/project/git-view 事件,Settings Export Diagnostics 经 Rust write_diagnostics 落盘 app_config_dir/diagnostics;0.6.13 §164 增量:面板只留导出按钮,读数进报告)
│       ├── stores/toastStore.svelte.ts
│       ├── stores/fileTreeStore.svelte.ts(每项目树态:expanded/pinned/foldersFirst,相对路径身份;恢复入口 restoreTreeState/restoreExpandedFolders;0.6.4+:展开/重展开/根一律强制重读,revealInTree 自动展开祖先链;**Phase 9:applyTreeRenames/pruneRemovedDirs——watcher 改名/删除先改路径键态再 refreshProject(§84/§83)**)
│       ├── stores/tabsStore.svelte.ts(每项目 FileTabState+内容缓存(SvelteMap——$state 深代理不包 Map,lessons L13);恢复入口 restoreTabs/ensureContentLoaded;激活/切换文件时 closeDiff 让位 diff 视图;**Phase 9:reloadFile(§82 单文件重读原语,Ctrl+R 与 watcher 共用;contentRev++ 驱动查看器换装)+applyTabRenames(§84 页签/缓存键/active 跟随改名)**)
│       ├── stores/errorDialogStore.svelte.ts(0.6.13:居中错误弹窗单槽)/
│       ├── stores/watcherStore.svelte.ts(Phase 9 编排:listen fs-changed→改名应用→refreshProject→开着的页签按需 reloadFile→refreshGitNow(**直取非防抖,L34:事件可在隐藏窗到达,定时器会冻**)→激活页签变了才 toast §82;**0.7.1 起单 lane 串行+忙时合并批次防堆积(L35),lane 内无 setTimeout**)/
│       ├── stores/gitStore.svelte.ts(Phase 7 运行时 git 态,§20 零持久化:每项目快照+marks 缓存;refreshGit 400ms 防抖/refreshGitNow 启动直取(隐藏窗口 timer 冻结,lessons L28);单槽 gitViewSlot(diff/commit 两态,0.6.8 返修;Git 视图接管主区时 App 隐藏 FileTabs);forgetGit 随项目移除)/
│       ├── stores/recentStore.svelte.ts(0.7.3 Open Recent MRU 态,§198:≤10 条 canonical 路径 record/remove/clear/restore;持久化搭 appState.recentFolders 可选字段与 stateSync 既有防抖车,零新增定时器)
│       ├── services/appState.ts(持久化纯函数:白名单序列化+自愈解析;0.7.3 recentFolders 可选字段——非空才写、读取截断自愈,恢复只 adopt 不 record)+ sessionRestore.svelte.ts(启动恢复编排:resolve 校验,失效项目跳过)+ stateSync.svelte.ts($effect.root 防抖 800ms 保存+pagehide flush)
│       ├── services/debugHook.ts(0.7.11:window.__aiv.snapshot() 只读探查钩子——projects/tabs 每根态/DOM 查看器身份(data-rel 对照)/日志环摘要;live-inspect.py 经 CDP 9322 直取,pre-0.7.12 客户端自动回退 DOM 比对)
│       ├── services/avatarColor.ts(0.7.14:rootPath FNV-1a hash→8 色板稳定徽标色+首字母,spec-014 D3)
│       ├── components/Icon.svelte(0.7.14:全应用唯一图标表——16 枚内联 SVG/2px 描边/currentColor,替换全部 Unicode/emoji 字形;FILE_ICONS 类型族映射消费 viewerType 路由,spec-014 D1/D4)+ services/viewerType.ts iconFamilyOf(类型图标族=查看器路由同源)
│       ├── constants/treeVisibility.ts(可见性过滤;8 名单唯一真值在 Rust file_tree.rs)
│       └── services/shortcuts.ts(P0 快捷键中央 dispatcher)/ tauri.ts(invoke 封装)/
│           treeSort.ts(显示序纯函数,§33–36)/ treeSort.test.ts(vitest)/ watcherIgnore.ts(§32 清单,与可见性分家;**Phase 9 起为 Rust watcher.rs 同款清单的 TS 侧镜像(注释互指,D8)**)/
│           watcherApply.ts(Phase 9 纯函数:needsReload 精确路径/isGone 含目录前缀/renamedRel 改名映射+vitest)/
│           recentList.ts(0.7.3 Open Recent 纯函数,§198:insertRecent MRU 去重截断+recentName/recentParent 行拆分,vitest 直测)/
│           viewerType.ts(扩展名→查看器路由)/ handoffMenu.ts(Phase 6:右键移交分型菜单构建,树/页签同源+剪贴板 toast)/
│           menuKind.ts(Phase 8 菜单分型纯函数,§142 切片:script/exe/msi,handoffMenu 消费+vitest 直测)/ gitFormat.ts(Phase 7 纯函数:badgeText §9/relativeTime §54——%ct 秒 Rust 侧 ×1000 转 ms(0.6.8 修 "56y ago")/marksByRel §46/letterClass 配色类)/ diffSideBySide.ts(0.6.8:unified→并排行拉链纯解析,DiffSegment/DiffRow)/
│           ContextMenu/menuPosition.ts(右键菜单视口钳制,0.6.3)
└── src-tauri/ —— Rust 后端
    ├── tauri.conf.json(窗口 1280×800/CSP/NSIS/dragDropEnabled:false——HTML5 拖拽必需,lessons L10)
    ├── capabilities/default.json(**0.7.6 最小授权**:core:default + dialog:default + opener:allow-open-url 限 http/https——渲染层不持有任何 open-path/reveal 能力,D10)
    └── src/
        ├── main.rs / lib.rs(插件装配+启动耗时命令+WebView2 加速键 COM 禁用+RunEvent::Exit 状态兜底写;**Phase 9:manage 单槽 Mutex<Option<WatchSlot>>——激活项目唯一监听,start 换槽原子停旧(D6)**)
        ├── project/manager.rs(resolve_project:canonicalize+校验,8 个单测;paths_exist=0.7.3 Open Recent 批量存性检查(置灰判据),async+spawn_blocking 守 L35,9 个单测)
        ├── state/(Phase 4:mod.rs 两命令+测试态闸门 AIV_STATE_FILE/拒访;persistence.rs 原子写+损坏隔离;migration.rs 版本路由,10 个单测)
        ├── file_tree.rs(list_directory:单层+§29 打标+hidden_count+越界拒;§176 块1)
        ├── file_inspect.rs(inspect_file/read_text_file/read_media_file/read_binary_file:§101 流水线+按编码解码+图片 data URL+PDF 原始字节通道(ArrayBuffer,100MB 顶),守卫全在 Rust 侧;**0.7.6 起四命令全 async+spawn_blocking——大文件读盘/base64 不上主线程,spec-011 P2**)
        ├── handoff.rs(Phase 6 §132 ExternalEditor 抽象=NotepadEditor/VSCodeEditor+§133 语义命令 edit_in_quick_editor/open_in_code_editor/reveal_in_explorer/open_with_default_app/open_in_browser;全部先 canonicalize 校验(§143/§144);VS Code 探测=Local\Programs→Program Files→PATH 的 code.exe,11 单测)
        └── run.rs(Phase 8 运行层:run_project_script/run_project_executable 两语义命令;§117/§118 持久宿主策略=cmd /K+powershell -NoExit+CREATE_NEW_CONSOLE(实验定,spec-008 §一);**0.7.6:cmd /K 脚本路径走 SpawnArg::CmdPath=raw_arg 双层引号 `""path""`——cmd 见元字符剥单层引号重析,实证 a&calc& 文件夹可注入跑 PATH 命令(D11)**;§120 无 -ExecutionPolicy;§121/§124 cwd;扩展名白名单住 Rust;spawn 后即忘零驻留)/ git.rs(Phase 7 只读 Git Review:git_snapshot/git_diff/git_commit_detail 三命令(**0.7.1/0.7.6 全 async+spawn_blocking——起 git.exe 的重活禁上主线程,L35+spec-011 P1**;0.6.8 增 show 详情:改名/作者/文件,hash 消毒;**0.7.6:产生补丁的 diff 与 commit 视角 show 全带 --no-ext-diff/--no-textconv——曾漏 show 两处,§70**);§65 全部 git -C <GitRoot>+§70 安全旗标 --no-pager/quotepath=false/--no-optional-locks;porcelain=v2 解析(renamed TAB 双路径实证)+Scope 过滤换算项目相对路径;§72 diff 流式截断 2MB/20k 行+10s 超时+CREATE_NO_WINDOW)
        └── watcher.rs(Phase 9 监听层:notify-debouncer-full 400ms 单槽+start/stop_project_watch 两命令——**0.7.2 起均 async+spawn_blocking,监听生命周期永不进主线程(L35/L36)**;**NoCache 换 FileIdMap(L36:Windows 默认缓存会在 watch() 全树 WalkDir+逐文件开句柄,真实仓库分钟级卡死主线程)**;§32 忽略清单 Rust 侧路径段过滤(事件不跨 IPC,§80);**Windows rename=单事件 Name(Both) 带 [from,to],拆成相邻 From/To 再配对(lessons L33,§84)**;storm 上限 200/窗折叠全量刷新;spawn_watcher 泛型 sink(生产=emit/测试=mpsc);canonicalize 围栏;单测含真监听冒烟)
```

| 改什么功能 | 去哪个文件 |
|---|---|
| 项目增/删/去重逻辑 | src/lib/stores/projectStore.svelte.ts + src-tauri/src/project/manager.rs |
| Open Recent 最近文件夹(0.7.3,§198) | stores/recentStore.svelte.ts(态)+ services/recentList.ts(纯函数)+ components/ProjectTabs/AddProjectMenu(+ 号菜单)+ EmptyState(只读列表)+ projectStore.addProjectFromPath(记录点)+ project/manager.rs paths_exist(置灰)+ appState recentFolders(持久化) |
| 顶栏标签 UI / 右键菜单 | src/lib/components/ProjectTabs/ProjectTabs.svelte |
| 右键移交条目(树/页签/项目,§135–141 分型唯一真源) | src/lib/services/handoffMenu.ts(菜单构建+剪贴板)+ src-tauri/src/handoff.rs(命令) |
| 侧栏 Files/Git/Settings(含头部 ↻ Refresh 图标,0.6.5/0.6.6) | src/lib/components/SidebarHeader + SidebarPanels |
| 运行脚本/程序+项目信任(Phase 8) | src-tauri/src/run.rs(运行层) + projectStore.trustedForExecution(§129 门,前端 UX 门+Rust 扩展名/路径围栏) + handoffMenu.runWithTrust(§128 确认框+§119:成功静默/失败居中弹窗) + ExecutableInfoViewer + ErrorDialog |
| Git 只读检视(徽标/页签 ✓●/树标记/Git 面板/并排 diff/提交详情/刷新触发,Phase 7+0.6.8 返修) | src-tauri/src/git.rs(命令+解析) + src/lib/stores/gitStore.svelte.ts(态+防抖) + gitFormat.ts/diffSideBySide.ts(纯函数) + GitPanel(0.6.8 照 VS Code 重排:分段文件名/计数徽章/提交图形列)/DiffViewer/CommitDetailView 组件 |
| 文件变化实时监听(Phase 9:树/查看器/Git 自动刷新+删除改名同步) | src-tauri/src/watcher.rs(监听+防抖+忽略+配对) + stores/watcherStore.svelte.ts(批次编排) + services/watcherApply.ts(纯匹配) + tabsStore.reloadFile/applyTabRenames + fileTreeStore.applyTreeRenames/pruneRemovedDirs + App.svelte(激活项目 start/stop effect+initWatcher) |
| 主题/外观 tokens | src/app.css + stores/settingsStore.svelte.ts |
| 现场冻结/内容不一致取证(活体直连) | scripts/e2e/live-inspect.py(CDP 9322 只读,不启不杀)+ src/lib/services/debugHook.ts(__aiv 快照)+ freeze-probe.py(本地复现探针;诊断日志导出=Settings→Export Diagnostics) |
| 快捷键拦截/新组合注册 | src/lib/services/shortcuts.ts(禁用浏览器加速键在 src-tauri/src/lib.rs) |
| 窗口/安全策略 | src-tauri/tauri.conf.json |

## 4. 硬规则(代码层面必须守的)

- **内存最小化是第一实现原则**(owner 2026-10-02 立规,V1.5 §6 增量修订):每个开发决策(选型/数据结构/缓存策略/生命周期)都过内存秤——能不驻留的不驻留、能延迟加载的延迟加载、用户关闭的就真正释放;"先做完再优化内存"不被接受。落地参照:查看器懒加载(§94)、PDF 每文档独立 worker+关最后页签引擎归零(lessons L15)、非激活查看器卸载(§160.5)、大文件守卫在 Rust 侧(§104/§106)。新功能交付时主动报内存账。
- **起外部进程或读大文件的 Tauri 命令一律 async+spawn_blocking**(0.7.6 起,L35/L36 的泛化):同步命令跑在原生主线程,git.exe/大文件读盘在那里就是冻窗;0.7.1 git_snapshot、0.7.6 git_diff/git_commit_detail/read_text/media/binary/inspect 全部已转。新命令默认 async,同步命令里禁 IO/进程。
- **渲染层插件授权最小化**(0.7.6 起,spec-011 R20):capabilities 只授前端实际调用的能力(现仅 opener open_url http/https);Rust 侧经插件自由函数的调用不受 scope 影响,不许"顺手"给渲染层留授权。
- 一切文件/进程操作遵守 V1.5 §143–§147:路径 canonicalize 后按 Path 语义校验在 Project Root 内;进程一律 Executable + Args Array,禁止 shell 字符串拼接(**cmd.exe 的 /K 载荷走 raw_arg 双引号**,architecture D11);前端无任意执行命令。
- git 一律 `git -C <GitRoot>` 执行(输出基准统一,见 §196 附注A);**产生补丁的 git 调用(diff/show)必带 --no-ext-diff --no-textconv**(§70,0.7.6 起含 commit 视角)。
- Viewer 只读:任何情况下不得引入编辑能力(V1.5 §5)。
- 每个 Phase 必须:编译→运行→测试→benchmark(如需)→报告→停,等 owner 确认(V1.5 §191)。
- 标识符英文,文档中文;首个密钥引入当天建《密钥总备份》(目前零密钥,不建空账)。

## 12. 修订记录(架构决策变更必记:谁拍的、推翻了什么)

| 日期 | 版本 | 变更 | 触发 |
|---|---|---|---|
| 2026-10-26 | 0.8.13 | **正式安装版落地**:webviewInstallMode=**offlineInstaller**(离线大包 ~210MB,setup.exe 单文件拷走即装);CDP 端口门禁按渠道标识收口(D13 债清偿——`.exp`/debug 保留 9322,默认标识+release 永不设;merge_webview_args 纯函数+6 单测+正式版启动实证零监听);V1.5 §197 审计行 | owner 2026-10-26 拍板"离线大包"(webviewInstallMode 三选一,spec-011 收尾遗留) |
| 2026-10-12 | 0.7.14 | **异地备份建线**(挂账清偿):remote `backup`=GitHub SSH(github_wzz 账号级钥匙),首推 main+核 0;备份规则八条落 §0(节奏/核账/force 语义/装不下红线/恢复/演练/第二平台预留/私有可见性=owner 确认项) | owner 指令(原计划 V1 后自建,提前委托) |
| 2026-10-12 | 0.7.14 | 视觉改版落地(spec-014,owner 拍板 A 克制专业/一步到位/亮色为主,布局不动):tokens 三档字阶+语义色统一(--danger 唯一错误红,--accent-soft 染色层)+暗色三面阶梯+Icon.svelte 内联 SVG 图标集(16 枚,替换全部 Unicode/emoji)+项目首字徽标 hash 色身份+文件类型图标族(路由同源)+两级标签正交(项目条 40px 底条/文件条 28px 顶线)+交互态 100ms 过渡;对比度 WCAG AA 全数值实测(含 2 处返修:亮面徽标字母压暗/Up-to-date chip 分主题);e2e 断言与字形解耦(徽章去括号+指示器 data-state);**D14** | owner"整个页面设计得特别土…调用 frontend-design 和 impeccable";评审 19/40 后拍板 |
| 2026-10-12 | 0.7.10–0.7.13 | T3 全量性能档跑通(A–I+Baseline 全过;idle 200MB 记账未达 150 目标,WebView2 基座占大头,非门);内容冻结大案修复:根因=ActiveViewer `$derived` 与 tabsState 失联跨项目蔓延 → 工作区按 rootPath keyed + projectTabs 返回 store 代理(**D12**);取证升级 0.7.11(data-rel 渲染标记/console 捕获/`__aiv.snapshot`);常开 CDP 9322 探查端口(**D13**);0.7.13 置顶图钉移行尾(层级对齐,owner 提案) | owner 报障"切页签内容不变"+活体直连指令;T3 预授权"开跑" |
| 2026-10-12 | 0.7.8/0.7.9 | 全面 code review 后修复批(spec-012,报告 44 条):同步命令 IO/进程清零(13 命令补转 async+updater exists() 前置门)、watcher 升 WatchState 代次(切换乱序自弃)、gitStore 单飞、PDF 三处取消语义(RenderTask cancel/搜索代次/scrollTimer+lastScrollTop 兜底)、open_with_default_app 可执行拒绝表(msi 豁免 §126)、CSP 补 base-uri/form-action 'none'、md5→RustCrypto md-5;0.7.9 返修=右键动作后树高亮保持(L41)。硬规则未变(0.7.6 已立),本批=全量执行;L29 警示重申:GUI 二进制只认 tauri CLI 产物 | owner"开工,完成spec012";InTest 报障返修 0.7.9 |
| 2026-10-11 | 0.7.6 | Phase 10 体检落地(spec-011):审计 20 项(九泄漏+十一风险)逐项留证;修三缺口+两主线程隐患——git show 补 §70 旗标、cmd /K raw_arg 双引号防注入(D11)、opener 授权收紧到 open_url http/https(D10)、git_diff/git_commit_detail+四读通道全转 async;发版三决定拍板(NSIS/不签/关更新,Q1 归档);硬规则新增"外部进程/大文件命令一律 async"+"渲染层插件授权最小化"+"产生补丁的 git 调用必带双旗标" | owner"开工"(Phase 10 A2 对齐) |
| 2026-10-02 | — | 基建落地:体验版客户端与更新机制(SPEC-INFRA-001)——owner 客户端独立 identifier/目录/数据,开发构建永不触碰;交付=scripts/publish-experience.ps1+客户端内 Update 按钮(md5 判定+rename 自替换);诊断面板加 Channel/Build 时间 | owner 立规("根治开发/体验共用 exe") |
| 2026-10-01 | — | Phase 5 落地:PDF.js Spike→完整查看器(specs/spec-005);pdfjs-dist 6.3 **legacy build**(modern 在 WebView2 143 缺 upsert 提案 API,lessons L14)+Vite worker+字节通道 read_binary_file(ArrayBuffer);CSP 加 worker-src 'self' blob:;虚拟化+切离释放+pdfState 持久化;§98 Benchmark 四场景落 testing.md §2e | owner 指令(§179) |
| 2026-10-01 | — | Phase 4 落地:Session & Settings(specs/spec-004)——AppState.version=1+防抖 800ms 原子写盘+迁移骨架+会话恢复(懒读内容);showSystemFolders 全局化(§22 对齐)、sidebarMode/Width 入 ProjectSession(§17);contentCache 改 SvelteMap(lessons L13);测试态闸门 AIV_STATE_FILE | owner 指令(§178) |
| 2026-10-01 | — | Phase 3 落地:File Tabs+五查看器+五快捷键真行为(specs/spec-003);新依赖 markdown-it/CodeMirror 6/opener/base64;测试模式 AIV_HIDDEN/AIV_TEST_PROJECT(零前台,testing.md §1) | owner 指令(§177) |
| 2026-10-01 | — | Phase 2 落地:specs/ 体系(根目录,spec-NNN)+ docs/workflow.md 状态机 + 文件树/收藏/文件识别(specs/spec-002);新依赖 encoding_rs、vitest;文件树默认 UI 偏好 Name+Folders First(§17 未定,取 VS Code 惯例) | owner 指令(§176) |
| 2026-10-01 | — | Phase 1 落地:Tauri 2.12 + Svelte 5.57 纯 Vite 工程建立(剥掉模板 SvelteKit);WebView2 浏览器加速键改 COM 禁用(Tauri 2 无配置项);Phase 1 Baseline 落 testing.md | owner 指令(§192) |
| 2026-10-01 | — | 建仓:V1.5 FINAL 定稿入库,按 AI-Project-Guide 阶段 0 建立基础文档;D1–D9 从 V1.5 提炼落表 | owner 指令 |
