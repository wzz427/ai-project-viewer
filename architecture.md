# architecture —— AI Project Viewer 技术架构(怎么做)

> 记录技术选型与实现结构。需求与开发顺序见《AI Project Viewer 产品需求与技术设计文档 V1.5 FINAL.md》
> (唯一基线,兼任 spec),交接见 docs/handoff.md,测试规范见 docs/testing.md(未建)。
> **§0 开发环境是建仓第一天就填实的**,其余随项目长。

## 0. 开发环境与跑法(新 agent 第一站;判据:只读这节就能把项目跑起来)

| 项 | 值 |
|---|---|
| 解释器 / 运行时 | 前端 Node v24.14.0(npm 11.9.0 / pnpm 11.1.3);Rust rustc/cargo 1.98.1 stable(x86_64-pc-windows-msvc,rustup 用户级安装于 `%USERPROFILE%\.cargo`;MSVC 链接器由已有 VS 2022 Build Tools 提供,hello-world 编译运行已验证)。⚠️ 安装后仅新终端 PATH 含 cargo,已开着的会话需 `export PATH="$USERPROFILE/.cargo/bin:$PATH"` |
| 包管理 | pnpm(前端,**仓库 `.npmrc` 固定 npmmirror 镜像**,npmjs 直连不通)+ cargo(crates.io 直连可通);Windows 11 + WebView2 Runtime 143 |
| 装依赖 | `pnpm install`(前端);Rust 依赖随首次构建自动拉取,`cd src-tauri && cargo fetch` 可预取 |
| 启动(开发) | `pnpm tauri dev`(起 Vite:1420 + debug exe);要可独立运行的 debug exe:`pnpm tauri build --debug --no-bundle` → `src-tauri/target/debug/ai-project-viewer.exe` |
| 跑测试 | 见 docs/testing.md §1(唯一真值):`pnpm check` / `cd src-tauri && cargo test` / 构建;Benchmark 档位见 V1.5 §162–§173 |
| 平台已知坑 | ① 路径含空格/中文必须加引号;② WebView2 浏览器加速键抢占应用快捷键 → 已在 Rust 侧 COM 禁用(§147,src-tauri/src/lib.rs);③ git 输出路径基准不一致:status 相对 cwd、diff/log 相对 Git Root,一律用 `git -C <GitRoot>` 规避(V1.5 §196 附注A);④ Rust `canonicalize` 产生 `\\?\` 前缀 → 用 dunce crate(V1.5 §144);⑤ 无 BOM UTF-8 的 .ps1 含中文会被 PS5.1 按 GBK 误读导致解析错乱(lessons L2) |
| 🚫 别碰 | 需求文档是唯一基线,不得未经 owner 修改;密钥文件别读(见 AGENTS.md 红线);不得绕过 V1.5 §143–§147 安全章节"图快" |

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

## 1.5 待决问题(摆上桌但"以后再说"的;不是 bug 不是待办,是没被遗忘也没被拍死的取舍)

| # | 问题 | 已知事实 | 何时回来评估 | 归档日 |
|---|---|---|---|---|
| Q1 | 发布形态(安装包格式/签名/自动更新) | V1.5 §184 已有初始建议:个人用 NSIS、updater OFF、签名非必需 | Phase 10 | |
| Q2 | Multi-Repository Workspace(一个 Project 含多个嵌套 repo) | V1.5 §66 明确不做,视为 Non-Git | 真实使用出现该痛点后(V1.5 §187 Future) | |

## 2. 整体拓扑(一张图;Phase 1 实测核实)

```
┌──────────────────────────── AI Project Viewer 进程树(7 进程,Phase 1 实测)────────────┐
│  Rust 主进程 ai-project-viewer.exe(Private 5.9MB,src-tauri/)                          │
│   ├─ project/(Phase 1 已建:canonicalize/去重);fs/ git/ runner/ external/ security/   │
│   │  state/ 待后续 Phase(V1.5 §157)                                                   │
│   ├─ 插件:single-instance(二次启动激活已有窗)/ dialog(文件夹选择、确认框)          │
│   └─ ↔ IPC(Tauri Commands:resolve_project / startup_elapsed_ms;清单见 V1.5 §159)    │
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
├── docs/
│   ├── handoff.md —— 交接页(现在在哪、上一段为什么)
│   ├── testing.md —— 测试档位+Baseline 真值
│   ├── how-to-report.md —— 汇报模板
│   ├── doc-maintenance.md —— 文档同步总表
│   ├── lessons.md —— 踩坑账
│   └── history/INDEX.md —— 历史归档入口
├── index.html / vite.config.ts / tsconfig.json / svelte.config.js / package.json / .npmrc —— 前端工程(纯 Vite+Svelte5,无 SvelteKit)
├── public/favicon.png
├── src/ —— Svelte + TypeScript 前端
│   ├── main.ts / App.svelte / app.css(主题 tokens,data-theme 切换)
│   └── lib/
│       ├── components/ProjectTabs/(顶栏项目标签:增/删/右键菜单/active)
│       ├── components/SidebarHeader/(Files/Git/⚙)
│       ├── components/SidebarPanels/(Files/Git/Settings 三个面板)
│       ├── components/EmptyState/(首启空态,V1.5 §151 文案)
│       ├── components/Toast/(单槽 toast)
│       ├── stores/projectStore.svelte.ts(内存态项目列表+去重+增删,持久化是 Phase 4)
│       ├── stores/settingsStore.svelte.ts(Theme,Phase 4 才持久化)
│       ├── stores/diagnosticsStore.svelte.ts(启动耗时/拦截计数,给验收当证据)
│       ├── stores/toastStore.svelte.ts
│       └── services/shortcuts.ts(P0 快捷键中央 dispatcher)/ tauri.ts(invoke 封装)
└── src-tauri/ —— Rust 后端
    ├── tauri.conf.json(窗口 1280×800/CSP/NSIS)
    ├── capabilities/default.json(core:default + dialog:default)
    └── src/
        ├── main.rs / lib.rs(插件装配+启动耗时命令+WebView2 加速键 COM 禁用)
        └── project/manager.rs(resolve_project:canonicalize+校验,8 个单测)
```

| 改什么功能 | 去哪个文件 |
|---|---|
| 项目增/删/去重逻辑 | src/lib/stores/projectStore.svelte.ts + src-tauri/src/project/manager.rs |
| 顶栏标签 UI / 右键菜单 | src/lib/components/ProjectTabs/ProjectTabs.svelte |
| 侧栏 Files/Git/Settings | src/lib/components/SidebarHeader + SidebarPanels |
| 主题/外观 tokens | src/app.css + stores/settingsStore.svelte.ts |
| 快捷键拦截/新组合注册 | src/lib/services/shortcuts.ts(禁用浏览器加速键在 src-tauri/src/lib.rs) |
| 窗口/安全策略 | src-tauri/tauri.conf.json |

## 4. 硬规则(代码层面必须守的)

- 一切文件/进程操作遵守 V1.5 §143–§147:路径 canonicalize 后按 Path 语义校验在 Project Root 内;进程一律 Executable + Args Array,禁止 shell 字符串拼接;前端无任意执行命令。
- git 一律 `git -C <GitRoot>` 执行(输出基准统一,见 §196 附注A)。
- Viewer 只读:任何情况下不得引入编辑能力(V1.5 §5)。
- 每个 Phase 必须:编译→运行→测试→benchmark(如需)→报告→停,等 owner 确认(V1.5 §191)。
- 标识符英文,文档中文;首个密钥引入当天建《密钥总备份》(目前零密钥,不建空账)。

## 12. 修订记录(架构决策变更必记:谁拍的、推翻了什么)

| 日期 | 版本 | 变更 | 触发 |
|---|---|---|---|
| 2026-10-01 | — | Phase 1 落地:Tauri 2.12 + Svelte 5.57 纯 Vite 工程建立(剥掉模板 SvelteKit);WebView2 浏览器加速键改 COM 禁用(Tauri 2 无配置项);Phase 1 Baseline 落 testing.md | owner 指令(§192) |
| 2026-10-01 | — | 建仓:V1.5 FINAL 定稿入库,按 AI-Project-Guide 阶段 0 建立基础文档;D1–D9 从 V1.5 提炼落表 | owner 指令 |
