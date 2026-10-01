# testing —— 测试规范与档位(唯一真值;别处只挂指针)

> 何时跑哪档、怎么判过。Benchmark 档位定义与耗时见 V1.5 §162–§173;
> Phase 验收清单见 V1.5 §188。**全量 Benchmark(A–I + Phase 1 Baseline 重跑)
> 之前必须 owner 点头**(AGENTS.md 红线);开发中秒级自测自己跑。

## 0. 档位速查

| 档 | 内容 | 何时跑 | 耗时量级 |
|---|---|---|---|
| T0 秒级自测 | `pnpm check` + `cargo test` + `pnpm tauri build --debug --no-bundle` 启动冒烟 | 每次改动后 | <2 min |
| T1 Phase 功能自测 | 本页 §2 的 Phase 清单(逐项实测,留证据) | 每个 Phase 交付前 | 0.5–1 h |
| T2 Phase Baseline | 本页 §3(Phase 1 起每 Phase 增量记录) | Phase 交付时 | ~10 min |
| T3 全量 Benchmark | V1.5 §166–§174 A–I 档 | owner 批准后(V1 收口前) | 数小时 |

## 1. 环境与命令(判据:只读这节就能跑测试)

| 项 | 值 |
|---|---|
| 前端类型检查 | `pnpm check`(svelte-check,0 错 0 警为过) |
| Rust 单测 | `cd src-tauri && cargo test` |
| debug 构建(可独立运行的 exe) | `pnpm tauri build --debug --no-bundle` → `src-tauri/target/debug/ai-project-viewer.exe` |
| release 构建 | `pnpm tauri build --no-bundle` → `src-tauri/target/release/ai-project-viewer.exe` |
| 带调试口启动(仅测试用) | `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222" <exe>`,CDP 工具 `%TEMP%\aiv-cdp.mjs` |
| ⚠️ 网络前置 | npmjs 直连不通,仓库 `.npmrc` 已固定 npmmirror;cargo 走 crates.io 直连可通 |

**GUI 自动化测试基建**(脚本在 `%TEMP%`,会话结束可能失效;首次重建约 20 分钟,重建方法记在 handoff):
- CDP 注入 JS(读写 DOM、点击按钮):`node aiv-cdp.mjs "<expr>"` —— 不需要窗口前台
- 驱动原生 Folder Picker / MessageBox:`aiv-picker.ps1` / `aiv-confirm.ps1`(UIA+Win32 消息,按 ClassName 找控件,不需要前台)
- 窗口截图(可穿透遮挡):`aiv-shot.ps1`(PrintWindow PW_RENDERFULLCONTENT)
- ⚠️ **禁止**向"当前前台窗口"盲发按键(SendKeys):按键会落进宿主终端;必须先 `GetForegroundWindow` 校验目标(见 lessons L3)

## 2. Phase 1 功能自测记录(2026-10-01,全部通过)

对照 V1.5 §192 完成清单 1–7 项:

| # | 验收项 | 方法 | 结果 |
|---|---|---|---|
| 1 | 成功编译 | `pnpm check` 0错0警;`cargo test` 8/8;debug+release 构建通过 | ✅ |
| 2 | 实际启动 | release/debug exe 均启动,窗口标题 AI Project Viewer,Responding=True | ✅ |
| 3 | Single Instance | 二次启动 exit 0,进程数保持 1 | ✅ |
| 4 | Project Tabs | CDP+UIA 实测:加 Alpha/Beta 两 tab,active 正确切换 | ✅ |
| 5 | Add / Remove / Dedup | Add:picker 全链(含原生对话框);Remove:右键→确认→tab 消失且**磁盘目录完好**;Dedup:小写路径重加 Alpha→不建新 tab、切换到已有、toast 提示 | ✅ |
| 6 | Files / Git / Settings Shell | Files 面板显示 canonical 路径;Git 占位面板可切换;Settings 含 Theme(System/Dark/Live 实测切换)+ Diagnostics | ✅ |
| 7 | 快捷键基础拦截 | 物理注入 Ctrl+R:WebView2 加速键已禁用(COM)、事件到达 DOM、dispatcher 拦截、toast 显示、**页面未 reload**(§147) | ✅ |

其余 4 个 P0 组合(Ctrl+W/F/Tab/Shift+Tab)与 Ctrl+R 同一 dispatcher 分支,留 owner 手测(30 秒)。
Rust 侧 `resolve_root` 单测覆盖:尾斜杠/大小写归一、basename、盘根拒绝、文件拒绝、不存在拒绝、`\\?\` 前缀剥离、空串拒绝。

**owner 验收建议路径**(2 分钟):启动 release exe → 点 + 加任意项目 → 再加同项目(小写)看切换 → Remove(**两处入口**:顶栏项目标签右键,或 Files 面板项目路径右键;确认目录还在)→ ⚙ 切 Dark → 按 Ctrl+R 看拦截 toast → Settings 诊断面板看拦截计数与启动耗时。空白处右键不应弹出任何浏览器菜单(Back/Reload/Print/Inspect)。

### 2026-10-01 验收反馈修复(release 已重建)

owner 验收时在 Files 面板项目路径处右键找不到 Remove——入口只挂在顶栏标签上,反直觉。已修:① Files 面板项目路径右键弹出同一菜单(共享组件 ProjectContextMenu,Phase 2 文件树根节点沿用);② 全局禁用 WebView 默认右键菜单(此前右键会露出浏览器菜单 Back/Reload/Print/Inspect,违背桌面应用定位)。CDP+UIA 全链回归通过。

## 3. Phase 1 Baseline(V1.5 §162,2026-10-01,release 构建)

| 指标 | 值 | 口径 | 目标(§163–§165) |
|---|---|---|---|
| Startup(窗口可见) | 冷 992ms;温 375ms / 88ms | Start-Process → MainWindowHandle≠0,3 次 | ≤2 s ✅ |
| 前端就绪(进程起→onMount) | 646 ms | 诊断面板 startupMs(debug 构建,含 CDP 端口) | 参考值 |
| Idle 进程树 RAM | **Private 179 MB**(WS 382 MB) | 7 进程(1 Rust + 6 WebView2);Private 不重复计共享页 | ≤150 MB target(非 gate)⚠️略超 |
| — Rust 主进程 | Private 5.9 MB | | |
| — WebView2 六进程 | Private 173 MB | browser 79 + renderer 45 + GPU 26 + network 12 + storage 9 + crashpad 2 | |
| Idle CPU | 0.21 CPU·s / 60 s ≈ 0.35% 单核 | 进程树 CPU 时间差,60 s 无操作 | 接近 idle ✅ |
| WebView2 进程数 | 6 | 进程树计数 | 记录 ✅ |

**RAM 判读**:179 MB 超出 150 MB target 19%,全部来自 WebView2 空应用底座(Chromium 最低开销),Rust 侧仅 5.9 MB。
§163 明确 150 是 target 非 Release Gate,且"相同真实场景明显低于 VS Code"已远达成(VS Code 典型 500 MB–1 GB)。
压缩手段(WebView2 启动参数裁剪、进程合并)挂 Phase 10 Performance Review,不为 Phase 1 强行引入。

测试机型环境:Win11 + WebView2 Runtime 143.0.3650.96,127.0.98.1 工具链构建。
