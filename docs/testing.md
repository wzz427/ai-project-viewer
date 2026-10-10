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

### 1.1 命令速查

| 项 | 值 |
|---|---|
| 前端类型检查 | `pnpm check`(svelte-check,0 错 0 警为过) |
| Rust 单测 | `cd src-tauri && cargo test` |
| debug 构建(可独立运行的 exe) | `pnpm tauri build --debug --no-bundle` → `src-tauri/target/debug/ai-project-viewer.exe` |
| release 构建 | `pnpm tauri build --no-bundle` → `src-tauri/target/release/ai-project-viewer.exe` |
| 带调试口启动(仅测试用) | `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222" <exe>`,CDP 工具 `%TEMP%\aiv-cdp.mjs` |
| ⚠️ 网络前置 | npmjs 直连不通,仓库 `.npmrc` 已固定 npmmirror;cargo 走 crates.io 直连可通 |

**GUI 自动化测试基建**(正典回归脚本已入库 `scripts/e2e/`(2026-10-10,跑法见其 README 与下方 §1.2/§1.3);一次性基建工具仍在 `%TEMP%`,失效后按本节方法重建):
- CDP 注入 JS(读写 DOM、点击按钮):`node aiv-cdp.mjs "<expr>"` —— 不需要窗口前台
- 驱动原生 Folder Picker / MessageBox:`aiv-picker.ps1` / `aiv-confirm.ps1`(UIA+Win32 消息,按 ClassName 找控件,不需要前台)
- 窗口截图(可穿透遮挡):`aiv-shot.ps1`(PrintWindow PW_RENDERFULLCONTENT)
- ⚠️ **禁止**向"当前前台窗口"盲发按键(SendKeys):按键会落进宿主终端;必须先 `GetForegroundWindow` 校验目标(见 lessons L3)
- 🔴 **测试一律零前台**(owner 2026-01 立规,含"不许窗口闪现"):脚本不得 SetForegroundWindow/AppActivate/SW_RESTORE 抢焦点。**标准测法**(spec-003 起):
  `AIV_HIDDEN=1 AIV_TEST_PROJECT="<夹具路径>" WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222" <exe>` ——窗口全程不显示、项目自动添加(免原生选择框)、CDP/Playwright 驱动;正常双击启动不受影响(窗口由应用显式 show)。
  ⚠️ 隐藏窗口收不到可信键盘输入(CDP Input 层)——测应用 dispatcher 用 **DOM 合成 keydown**(window.dispatchEvent);物理键盘链路属 Phase 1 验证项,未变。拖拽用 Playwright mouse;截图用 PrintWindow 穿遮挡。旧法 SW_SHOWMINNOACTIVE 已废弃(启动瞬间仍会闪)。

### 1.2 零打扰 GUI 测试规程(正典;owner 2026-10-09 立规"不许抢鼠标/不许弹窗")

**启动公式**(正典脚本已内置):`AIV_HIDDEN=1 AIV_TEST_PROJECT=<夹具> AIV_STATE_FILE=%TEMP%\<独立>.json WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<port> <release exe>` → 窗口隐藏启动后 **SetWindowPos 移屏幕外(-2500)+SW_SHOWNOACTIVATE**——保持渲染(最小化窗口的 caretRangeFromPoint/hit-test 读到的是过期布局,屏幕外才准),全程不可见不抢前台;真实 state 永不被碰(AIV_STATE_FILE 闸门)。

**输入分层(下药前先分层)**:

| 层 | 方法 | 测什么 |
|---|---|---|
| 页面内派发 | JS `new MouseEvent/PointerEvent` dispatch 到目标元素/window | **我们自己的 DOM 逻辑**(如 PDF 选择驱动)的完整路径;绕开可信合成的坑 |
| 可信 CDP | Playwright connect_over_cdp 的 mouse/keyboard | 原生路径、且场景中 JS 不写选区时;**盲区:JS 写过选区后,拖动中的可信 move 会被浏览器吞** |
| 真实输入层 | Win32 SetCursorPos/mouse_event;**坐标自校准 `屏幕=ClientToScreen 原点+CSS×(客户区宽/innerWidth)`(别乘 dpr——DPI 虚拟化下错 1.25 倍);手势前必查 GetForegroundWindow,丢了就点击自家未被遮挡区带回(WindowFromPoint 探测可见点;拖标题栏会变成拖窗口)** | 仅 owner 明确许可占用鼠标时,或最终交叉验收 |
| 官方 oracle | `scripts/e2e/oracle/oracle.html`(官方完整查看器驱动页;搭建见 e2e README) | 判定"我们的问题还是上游/内核"——动代码前先拿它定基线 |

**铁律**:①场景必须复刻 owner 原话手势(窗口是否最大化、出界方向、按住移动路径——历史上三轮假"修好了"全栽在场景不对齐);②疑内核问题先查 `navigator.userAgent` 的 WebView2 版本(143 有选择内核缺陷、155 修好;升级=离线包+管理员运行,引导器/winget 静默装对 per-machine 报 0x80040828);③断言写进脚本自判 PASS/FAIL,不留人工判读;④合成输入≠真实输入(L17),交付口径以 owner 亲手复验为准。

### 1.3 脚本清单(scripts/e2e/,正典入库 2026-10-10;跑法详见其 README)

| 脚本 | 覆盖 | 何时跑 |
|---|---|---|
| `pdf-selection-battery.py` | PDF 文本选择全场景(V1–V8:拖选/出界/反选原场景/行首垫/跨页/串台/宽屏/双击) | 凡动 PdfViewer/文本层/选择驱动 |
| `pdf-suite.py` | PDF 功能 19 项(渲染/翻页/缩放/搜索/虚拟化/释放/恢复/扫描件) | 凡动 PDF 相关 |
| `acceptance-r3.py` | 验收轮 8 项(更新按钮/任务清单/右键 Copy/文本层) | UI 通用改动 |
| `real-input-battery.py` | 真实鼠标 8 手势电池(app+官方对照双模式,前台守卫) | 仅 owner 许可占用鼠标时 |
| `oracle/` | 官方查看器对照基准 | 疑上游问题 |

一次性诊断脚本(sweep/fight-log/max-repro/stepwise/probe 等)不入库,配方在本文历史区与 lessons,需要时重建。

---

## 【历史记录区(append-only)】

> 以下是各 Phase/轮次的实测记录与证据链,**是账本不是手册**——"现在怎么测"只看 §0–§1.3;
> 修法与数字的来龙去脉在这里查。文中引用的 `%TEMP%` 一次性脚本属历史配方,正典以 §1.3 为准。

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

**owner 验收建议路径**(2 分钟):双击桌面快捷方式 **AI Project Viewer**(指向 release exe,重建后自动最新,别用复制出来的旧副本)→ 点 + 加任意项目 → 再加同项目(小写)看切换 → Remove(**两处入口**:顶栏项目标签右键,或 Files 面板项目路径右键;确认目录还在)→ ⚙ 切 Dark → 按 Ctrl+R 看拦截 toast → Settings 诊断面板看拦截计数与启动耗时。空白处右键不应弹出任何浏览器菜单(Back/Reload/Print/Inspect)。

### 2026-10-01 验收反馈修复(release 已重建)

owner 验收时在 Files 面板项目路径处右键找不到 Remove——入口只挂在顶栏标签上,反直觉。已修:① Files 面板项目路径右键弹出同一菜单(共享组件 ProjectContextMenu,Phase 2 文件树根节点沿用);② 全局禁用 WebView 默认右键菜单(此前右键会露出浏览器菜单 Back/Reload/Print/Inspect,违背桌面应用定位)。CDP+UIA 全链回归通过。

## 2b. Phase 2 功能自测记录(2026-10-01,全部通过;spec-002 V1–V5)

环境:debug 构建 + CDP(方法同 §1);fixture = `%USERPROFILE%iv-test-projects\TreeAlpha`(含 node_modules/.git/dist、GB18030 中文、NULL 二进制、5MB/21MB 文件、空目录;用后可删)。截图证据 `%TEMP%iv-p2-final.png`。

| §188 块 | 实测方式 | 结果 |
|---|---|---|
| File Tree:Lazy Load / 启动不递归 | 加项目后 DOM 只有根层;展开 src 才见 main.py+utils,展开 utils 才见 helper.py(逐层) | ✅ |
| .git/node_modules 默认隐藏,dist/build/target 默认显示 | 根层行序 dist,docs,empty_dir,src + 文件;隐藏者不在行内 | ✅ |
| Show system folders Toggle / 隐藏提示 / 两清单独立 | ⋯ 菜单开关即时生效(零 IO);提示行 "2 system folders hidden" 随之显隐;可见性 8 名单在 Rust file_tree.rs、watcher 11 名单在 services/watcherIgnore.ts,物理两个模块无共享 | ✅ |
| Name Sort × Folders First | 开=目录块在前;关=混排(alpha.txt<config.yaml<dist<…<zeta.txt 自然序) | ✅ |
| Favorites First / Pin 文件+文件夹 / 混排 / 同父约束 | Pin README.md+config.yaml+src → 置顶区手工序混排带 ★;Pin 只改显示序 | ✅ |
| Pinned Drag Sort | 拖 README.md 落到 src 前 → [config.yaml, README.md, src];drop 只收同父 Pinned 目标 | ✅ |
| Unpinned 自动排序 / 新文件落位 | 新建 alpha.txt 回归(重建)后落 Unpinned 区自动序,不带 ★ | ✅ |
| Rename 保位 / Delete 清 Pin | 盘上 README.md→renamed-doc.md 后 Refresh:置顶区原位换名;删 alpha.txt 后 Pin 记录真被清(重建同名回 Unpinned) | ✅ |
| File Inspection(§188 11 行) | cargo 单测 24 项:流水线顺序、UTF-8/BOM×3/GB18030/NULL 二进制、无 BOM UTF-16 判 binary(§103 已知限制)、4.9/5/20/20.1MB 边界、`..` 越界、目录拒绝 | ✅ |
| Path Persistence 相对路径身份 | store 数据形状照 §17/§19(`.`=根) vitest 9/9;写盘属 Phase 4 | ✅ |
| **排序红线(V5)** | 全程前后磁盘 md5 快照对比:仅测试脚本自身的 README 改名与 alpha 删除/重建,其余逐字节未动 | ✅ PASS |

未覆盖留 owner 手感项:拖拽手感(V-human)、⋯ 菜单视觉。inspect_file 的 UI 消费(状态栏编码/Large File 确认框)按 spec-002 随 Phase 3 第一个 Viewer 落地。

**owner 验收建议路径**(1 分钟,release 已重建,桌面快捷方式直接可用):双击 AI Project Viewer → + 加任意项目 → 展开/收起目录 → ⋯ 菜单切 Favorites First → 右键任一文件 Pin to Top(★ 置顶)→ 拖动置顶项换序 → 改一个文件名后 ⋯ → Refresh 看置顶保位 → 右键 Unpin。

### 2026-10-01 Phase 2 验收反馈返工(release 已重建)

owner 三条反馈,全部落地并实测:
1. **排序合一**:删 Name/Favorites 两模式(V1.5 §33 增量修订),恒为 Pinned 区+Unpinned 区;vitest 重写 10/10。
2. **Pin 拖拽修复**:根因 = Tauri Windows 默认 `dragDropEnabled:true` 劫持 HTML5 拖拽(lessons L10);`tauri.conf.json` 置 false 后**真实鼠标**(mouse_event 物理输入)拖 config.yaml 上移换序实测成功——此前 CDP 合成 DragEvent 假阳性。
3. **⋯ 并入 Settings**:⋯ 按钮删除;⚙ 点击进 Settings(File Tree 区:Folders First/Show system folders/Refresh + Theme + Diagnostics),再点 ⚙ 回 Files;实测切换与勾选生效。

复验 30 秒:双击桌面快捷方式 → 加项目 → 右键 Pin 两个文件 → **真鼠标拖动换序** → ⚙ 看 File Tree 区 → 取消 Folders First 看混排 → 再点 ⚙ 回树。

### 2026-10-01 二轮反馈:拖不到最顶(release 已重建)

owner 发现置顶项拖不到最顶部(拖到别处正常)。根因两层:① 落点语义只有"插到目标前",第一行上方的空白带(路径框+间隙约 30px)不接任何 drop,"甩到顶"就丢;② WebView2 要求 **dragenter 也 preventDefault** drop 才触发(lessons L10 补记)。修复:置顶行按光标上下半分"插前/插后"(顺带补上"移到最底"能力);面板级顶部区(光标高于第一个置顶行=插到最顶);行与面板同时挂 dragenter+dragover。验证:Playwright over CDP 三场景(甩顶区/最底半区/行内)全 PASS,零前台。


## 2c. Phase 3 功能自测记录(2026-10-01,spec-003)

夹具:**桌面 `AIV-TestProject`**(owner 指定建,31 文件:md/json/yaml/toml/txt/csv/log/py/ts/rs/css/html/sql/ps1/bat + png/jpg/gif/webp/svg + edge-cases[GB18030/UTF-16BOM/UTF-8BOM/二进制/5MB/21MB],两层嵌套子目录,含内嵌脚本的安全 SVG 样本)——owner 验收直接用它;旧 `aiv-test-projects\TreeAlpha` 可删。零前台模式跑 `%TEMP%iv-p3-read-test.py`(Playwright over CDP)。

| §188 块 | 实测 | 结果 |
|---|---|---|
| Markdown 10 行 | 默认 Rendered/表格/任务清单/代码块/本地图片(data URL)/内链开 Tab/Source 只读/Raw `<script>` 注入不执行 | ✅ |
| Text/Code 9 行 | txt/log/csv、py/ps1(嵌套深层)高亮行号、Ctrl+F 面板、只读 | ✅ |
| JSON/YAML/TOML 4 行 | JSON 默认 Formatted 可切 Source | ✅ |
| Images 7 行 | 五格式+SVG `<img>` 上下文+onload/script 双验证不执行 | ✅ |
| File Inspection 补 | GB18030 中文/UTF-16 BOM 正确解码(cargo 7 项单测+界面);binary/huge 两大守卫;5–20MB 确认框流程(Rust 侧单测覆盖) | ✅(utf16 自动化检查一次偶发竞态,三重人工验证过:Tab 开、内容对、行点击→内容 400ms) |
| Tabs/生命周期 | 多 Tab 增/切/关/去重/激活恢复;Ctrl+Tab 双向循环 | ✅ |
| 删除态 §83 | 删当前文件→Ctrl+R→"This file has been deleted."+[Close Tab] | ✅ |
| §147 正式验收 | Ctrl+R:树+活动文件刷新、页面**不 reload**(window 标记存活断言)、Tab 全保留;Ctrl+W 关当前 | ✅ |
| Rust | cargo test 38/38(read_text_file 五编码解码/BOM 剥离/binary/huge 拒/越界拒;read_media 五格式 mime/超大拒) | ✅ |

**owner 验收建议路径**(2 分钟,release 已重建):双击桌面 AI Project Viewer → + 加 `Desktop\AIV-TestProject` → 点 README.md(渲染/表格/任务清单/图片/链接)→ 点 main.py(高亮行号)→ Ctrl+F 搜 → 点 metrics.json(Formatted/Source)→ 点 assets\logo.svg(缩放/100%)→ 点 edge-cases\huge-21mb.log(守卫)与 chinese-gb18030.txt(中文)→ Ctrl+Tab/Ctrl+W/Ctrl+R 各试一次。

### 2026-10-01 十项验收反馈返工(release 已重建;回归 16/16 PASS,零前台)

① 内容不刷新(txt/html 显示旧文件)=缓存非响应式+同型查看器不重挂载→`{#key 文件}`+`$state(Map)`;② 图片看不了=二进制判定先于图片路由→扩展名优先媒体通道(lessons L12);③ 固定页签模型(当日二次澄清后):默认页签正常累积;右键 Pin Tab 固定后,新文件顶替未固定页签(📌 标记,无斜体预览态——首版 VS Code 式全预览被否);④ 页签右键菜单=模式切换(Markdown/JSON)/Keep Open/Open with Default App/Close,浮动切换窗删除;⑤ 页签可拖拽重排、激活自动滚入、高亮强化(顶部色条);⑥ 视觉:浅色阅读面纯白、字体栈 Segoe UI Variable+Cascadia、Settings→Viewer 可调字号;⑦ GIF 实测渲染;视频等应用外格式走右键"默认程序打开"(opener 直达播放器)。V1.5 §197 审计 4 行(§86/108 细化、§186 提前、§111 泛化)。复验 1 分钟:连点几个文件(页签正常累积)→ 右键某个页签 Pin Tab → 再点其他文件(顶当前未固定者;停在固定页签时顶最右未固定者)→ 把一个页签**甩到页签条最右端空白处**(末位可达;空白带死区已修,2026-10-01 二次追加)→ 右键 README 切 Source/Rendered → 拖动页签换位 → 点 assets\photo.jpg(应显示)→ 右键 icon.gif "Open with Default App"(系统看图打开)。

## 2f. SPEC-INFRA-001 体验版客户端与更新机制(2026-10-02;回归 8/8)

**交付流程从此改版**:owner 的客户端=%LOCALAPPDATA%\AIProjectViewerpp\(独立 identifier `.exp`,与开发构建彻底隔离,数据/单实例互不可见);桌面快捷方式已重指。**每轮交付**:`powershell -File scripts/publish-experience.ps1 -Note "本轮改了什么"`(构建+放 updates 目录)→ 通知 owner → 他点客户端右上角 Update(置灰=无更新/高亮=有,悬停看说明)→ 一键更新,可选立即重启。开发侧任何构建/测试不再触碰他的进程(并存已断言)。

机制:更新判定=exe 内容 md5(流式);替换=复制→校验→旧文件 rename .old→新文件正名(Windows 允许 rename 运行中 exe),启动时清理残留;原生确认对话框(TaskDialog)在测试态自动选 Later(test_mode_active,TaskDialog 无子 HWND 不可驱动,L7 补记)。首次安装:`scripts/install-experience.ps1`(装机+迁移 state+快捷方式,已完成)。

回归 `%TEMP%iv-infra1-test.py` 8/8:高亮+note/一键更新+toast+按钮回灰/重启后新版(Channel=experience+Build 变化)/无更新置灰/**开发版与体验版并存互不退出**。防退化:P3 PASS+PDF 19/19。体验版测试启动式与开发版相同(AIV_HIDDEN/AIV_TEST_PROJECT 同样生效,无 AIV_STATE_FILE 时不碰它的真实 state)。

## 2d. Phase 4 功能自测记录(2026-10-01,spec-004;全部通过)

状态文件:`%APPDATA%\com.aiprojectviewer.app\state.json`(JSON,version=1);写盘=800ms 防抖+同目录 tmp→flush→原子替换,退出时前端 pagehide+Rust RunEvent::Exit 双兜底。测试态闸门:`AIV_TEST_PROJECT` 设置且未给 `AIV_STATE_FILE` → 读写均不碰真实 state(owner 状态永不被测试污染);给了则读写该独立文件。

| 档 | 内容 | 结果 |
|---|---|---|
| cargo 48/48 | state 模块 +10:原子写往返/无 tmp 残留/损坏 JSON 隔离自愈/缺 version 拒/未来版本拒/合法 v1 载入/迁移路由×3/测试闸门路由 | ✅ |
| vitest 18/18 | appState +8:相对路径身份(除 rootPath 外无盘符)/FileTabState 白名单(runtime 字段不落盘)/容器拷贝不泄漏/往返一致/坏 JSON 与错版本拒/字段级自愈(fontSize 钳制、坏 viewerType 丢 tab、坏 sidebarMode 回 files) | ✅ |
| svelte-check | 0 errors / 0 warnings | ✅ |
| CDP 持久化回归 24/24 | `%TEMP%\aiv-p4-state-test.py`(AIV_STATE_FILE 独立文件,零前台):防抖非即时写/落盘结构(version/相对路径/激活页/主题/字号/全局开关/每项目 foldersFirst)/**重启恢复**(页签+激活页+内容懒读+主题+字号+sidebarMode+两个树开关)/损坏自愈+隔离备份/测试态不碰真实 state | ✅ |
| Phase 3 回归 17/17 | aiv-p3-fix-test.py 复跑(SvelteMap 改动的防退化) | ✅ |

**开发中发现并修复**:contentCache 原为 `$state(new Map())`——Svelte 5 深代理只包 plain object/array,**Map 零响应性**,会话恢复的页签永久卡 Loading;换 `SvelteMap`(svelte/reactivity)后全绿(lessons L13)。正常开文件路径此前一直正常纯属时序巧合(先 set 缓存后写 active 字段,对象字段写顺带触发了 derived),该坑自 Phase 3 就埋着。

### 2026-10-01 追加:侧栏拖拽调宽(owner 验收后拍板"要拖拽";回归 7/7 PASS)

侧栏右缘分隔条(4px,悬停/拖动高亮):鼠标拖拽 200–600px、拖动中全局 col-resize 光标+禁文本选择;分隔条可聚焦(Tab),←/→ 步进 16px(role=slider+aria 值,Svelte a11y 0 警告);宽度按项目写入 ProjectSession.sidebarWidth,防抖 800ms 落盘,重启还原。普通鼠标事件(非 HTML5 DnD),CDP mouse API 可信输入直接可测——脚本 `%TEMP%\aiv-p4-resize-test.py`:拖宽 260→440 生效/防抖写入 state.json/狂拖上限 600 钳制/键盘步进/重启宽度还原。

**owner 验收建议路径**(1.5 分钟,release 已重建):双击桌面 AI Project Viewer → + 加 `Desktop\AIV-TestProject` → 展开一两层目录、右键 Pin 一个文件 → 开两三个文件页签 → ⚙ 改 Theme=Dark、字号 + 两次 → **完全关闭应用** → 再双击打开:项目标签、展开、置顶、页签(含激活页和 Rendered/Source 模式)、主题、字号应全部还原;点开恢复的页签内容正常显示(大文件不弹确认);关掉重开 Settings 确认两个开关还在。

## 2e. Phase 5 功能自测记录(2026-10-01,spec-005;全部通过)

路线(spike 实测回填 spec-005 D1–D3):pdfjs-dist 6.3 **legacy build**(modern build 对原生 Map 调 `getOrInsertComputed`——upsert 提案 API,WebView2 143 没有,渲染全炸,lessons L14);Worker 走 Vite `?worker` 打包(同源,CSP 仅加 `worker-src 'self' blob:`);PDF 字节走 `read_binary_file`→tauri ipc Response→ArrayBuffer(100MB 硬顶),`getDocument({data})`;asset protocol 未启用。夹具=桌面 `AIV-TestProject\pdf\`(生成脚本 `%TEMP%\aiv-p5-make-fixtures.py`:10 页文本/100 页文本/100 页扫描 18.4MB/tab-1..5)。

| 档 | 内容 | 结果 |
|---|---|---|
| cargo 49/49 | read_binary +1:字节读回+越界拒 | ✅ |
| vitest 19/19 | appState +1:pdfState 序列化/自愈(page≥1、zoom 0.1–5、zoomMode 白名单) | ✅ |
| svelte-check | 0/0 | ✅ |
| CDP PDF 回归 19/19 | `%TEMP%\aiv-p5-pdf-test.py`(零前台,**debug+release 双跑**):首页渲染/总页数/真 worker(无 fake-worker 回退)/上一页下一页/跳页/缩放/自定义缩放/Fit Page/Fit Width/Ctrl+滚轮/搜索命中跳页/无结果反馈/深滚 canvas≤6(虚拟化)/当前页跟踪/切离释放/切回恢复/18.4MB 扫描件渲染/无页面错误 | ✅ |
| 防退化 | Phase 3 回归 PASS、Phase 4 持久化 24/24、侧栏拖拽 7/7 | ✅ |

### V1.5 §98 PDF Benchmark(release 构建+CDP 口径,2026-10-01)

| 场景 | before open | after open | deep scroll | switch away | close |
|---|---|---|---|---|---|
| A 10 页文本 | 406.2 | 540.6 | 543.3 | 553.9 | 555.2 |
| B 100 页文本 | 401.1 | 533.4 | 565.8 | 576.0 | 551.3 |
| C 100 页扫描(18.4MB) | 395.9 | 684.4 | 831.7 | 705.3 | 709.0 |
| D 5 个 PDF Tab 仅 1 激活 | 388.2 | 727.7 | — | 699.6 | 692.6 |

(单位 MB,进程树 RSS;脚本 `%TEMP%\aiv-p5-bench.py`,psutil 按命令行过滤本应用进程)

**判读**:①"before open"≈400MB 是 **CDP 调试底座**(测试必须开 remote-debugging;Phase 1 无 CDP 基线 179MB),四场景同底座,**看差值**;②开一个文本 PDF ≈ +134MB(pdfjs 模块+worker+首屏渲染),100 页与 10 页几乎同(**§95 虚拟化生效**,文档大小不主导常驻);③扫描件 +288/深滚 +436(大位图,真实代价);④**D:5 个 Tab 仅 +340MB,远低于 5×134,§188"多 PDF Tab 不线性吃 RAM"成立**(非激活 Tab 只有字节缓存+轻量状态);⑤close 后不立即回落是 Chromium GC 归还延迟,switch/close 同量级=无泄漏性增长。

**owner 验收建议路径**(1 分钟,release 已重建):打开应用 → `AIV-TestProject\pdf` → 点 sample-10p-text.pdf(渲染/工具栏)→ 翻页/跳页/缩放/Fit Width/Fit Page/Ctrl+滚轮 → 搜索框输 "Page 8"(跳页+计数,上一处/下一处)→ 滚到深页(只有窗口内的页在渲染)→ 切到别的文件再切回(页码/缩放/滚动还原)→ 点 sample-100p-scan.pdf(18.4MB 扫描件)→ 关掉重开应用,PDF 页签与页码还在(§93 持久化)。

## 4. 验证体系 v2 的演进史(2026-10-09 立;**现行正典已上移 §1.2,本节起是历史**)

起点教训:CDP 合成鼠标与真实鼠标**不走同一条选择代码路径**(L17)——两轮"合成验证通过、真机失败"后立。后续按轮次演进:真实输入层(自校准坐标+前台守卫)→ 零打扰三件套(隐藏+屏幕外+CDP)→ 页面内派发(驱动自驱逻辑)。下列轮次记录保留原始证据链;其中"dpr 保真"手段(Emulation.setDeviceMetricsOverride=deviceScaleFactor 1.25)仍用于几何断言、宽屏模拟。

### PDF 划词调查:已解决(2026-10-09 owner 选 A,升级+实证当天闭环)

**前情(143 时代,证据链)**:同页面(官方对照页)同手势三环境——Chrome 154=12 字 1 行 ✓;本机 WebView2 143=185 字 2 行 ✗。当时结论"WebView2 文本选择内核对'绝对定位+transform 透明文本层'有缺陷,v11 代码无罪"。

**A 方案执行**:Evergreen Runtime 143→**155.0.4283.45**。坑:官方引导器/winget 静默装都报 `0x80040828 已为系统安装`(per-machine 安装无管理员权限时直接放弃,连 UAC 都不弹);**唯一可行=离线包以管理员运行**(`Start-Process -Verb RunAs MicrosoftEdgeWebView2RuntimeInstallerX64.exe /silent /install`,winget 下载源直链+验签)。本机 EdgeUpdate 自动更新通道疑似停摆(Edge 也停在 140),以后再遇内核问题照此手动升级。

**升级后判决(真实输入层,自校准坐标+前台守卫)**:同电池 8 手势,官方对照页与 app **逐项打平全绿**——单击 0 字符 ✓;长拖 0.25→0.75=47~48 字符**1 行** ✓(对照页同);0.3→0.5/0.3→0.6 ✓;**右往左拖 ✓**;小拖 0.12 行宽=11 字符 ✓;**双击选词='brown' 5 字符 ✓**。中途两次假象勿重蹈:①"残余蔓选 461/569 字符"=我脚本坐标落进行间隙(DPI 虚拟化错 1.25 倍);②"手势突然全死"=owner 点回聊天窗口抢走前台,真实鼠标打到了别的窗口(selectionchange=0 是特征)。回归脚本 `%TEMP%iv-battery-replica.py`(mintest/app 双模式+前台守卫)。**owner 复验前提:把 app 完全退出重开**(运行中的实例仍挂着旧内核进程,重启才加载 155)。

### 155 后三轮收尾(2026-10-09 深夜;owner 报"最大化右出界蔓选+行首精度";已修+发布 v13)

owner 补充关键复现条件:**窗口最大化**、划到行尾继续右移出文字区 → 当前行往上全部蔓选(右出界,与我此前测的左出界不同侧!);另:行首字符稍左一点选不中。机理(官方 oracle 对比后确认):
- pdf.js 的 span 无行盒,文字侧空白列**无任何选择 quad**,Chromium 拖选延伸落进无字列时焦点直接跳文档起点(=蔓选);**官方查看器同样行为**(oracle 1182c/12L)——非我们移植错,但要按 Adobe/Chrome 体验修。
- 行首起选失败:空白垫无文字节点,Chromium 不肯在"无字区域"起锚。
修复(三层):span 加 20px 命中垫(padding+负 margin,字形/选区绘制不动——range 矩形只跟文字走);mousedown 落垫时手动锚定最近字符(caretRangeFromPoint);拖动中 rAF 每帧钳制——指针在行旁空白时把选区终点钳回该行文字端(**原生更新晚于 pointermove,一次性纠正是输家,帧循环才赢**)。
- **串台 bug(重要)**:垫内起选手势的驱动若未随 pointerup 干净退出,残留循环会用**下一个手势的指针位置**续写旧锚点的选区(146c=旧行锚点×新指针位置的跨行选区,数字对账锁定)。修=驱动单例:新手势 mousedown 先杀旧驱动+8s 超时自毁+pointercancel 兜底。
验证:**零打扰合成层**(owner 立规 2026-10-09 晚"不许再抢鼠标"):AIV_HIDDEN 启动+窗口移屏幕外(-2500)保持渲染,CDP 合成输入,Emulation.setDeviceMetricsOverride 模拟最大化宽度——污染复现→修复后垫手势后边距出界=54c/1L、宽屏右出界=38c/1L、电池/r3 8/8/PDF 19/19 全绿。**合成层盲区**(记档):拖选进行中合成 pointermove 会被浏览器吞(12 步只到 2 步),垫内起选全程无法合成驱动——该路径由真鼠标验证过(49c),驱动单例修复不影响其正向路径。pad 起选/最大化右出界的最终确认=owner 在 v13 亲手复验。

### 155 后四轮终版(2026-10-09 深夜;owner 报"按住划选+空白区上下移动→反选";v14 重写驱动)

owner 复验 v13 后再报:**按住划选一串词,鼠标移到右侧空白上下移动几下,原选区消失、之外的字符全被选上**(反选状)。根因= v13 驱动的锚点对原生手势是**每帧动态读**(`sel.anchorNode`)——原生在无字列会把锚点本身拖到文档边缘,污染后的"基准"被钳制循环放大,两个写入方拉扯出反选怪态。
**v14 设计(终版):拖选全程自驱**——锚点在 mousedown 瞬间用 caretRangeFromPoint 钉死(按下即定,永不再读);每帧把终点钳到**指针最近的文本行**(跨页也支持,行集合取全部已渲染页);双击/三击/shift 扩展/键盘选择保持原生(detail≥2 或 shiftKey 直接放行)。驱动单例+8s 自毁不变。
验证(**零打扰,页面内派发 mousedown/pointermove/pointerup**——非可信事件可完整驱动我们的 DOM 监听,顺带绕开"可信合成输入在 JS 写选区后被吞"的盲区):**owner 原场景=60c/1L 锚点稳定**;远端上移=锚点到目标行的连续选区;左右出界/行首起选/跨页/双击/污染场景全对;r3 8/8;PDF 19/19。v14 已发布。

### 155 后二轮收尾(2026-10-09 晚,owner 报两症状;已修+发布 v12)

owner 复验发现:①选行时**页面左上角出现跟随选区的色块**;②拖选中鼠标进入文本外侧空白,**上方所有行被整页选中**。根因都是"官方查看器机制没抄全"(同源、非内核):
- ①pdf.js 行间 `<br>` 无定位规则、静态流位置全叠在层左上角(官方同样如此),官方用 **`br::selection{background:transparent}`** 画成不可见——我们漏抄,br 亮成色块。
- ②文本层**容器**继承了全局 `.viewer-body` 的 `user-select:text`,指针落在空白(不可选)时浏览器找"最近可选祖先"=容器,焦点蔓上容器=整页包裹选。官方结构=**页面空白不可选、仅 span 自带 `user-select:text`**;另补官方 `endOfContent` 盾片(选择期间铺满层、`user-select:none`,空白拖选焦点弹回最近文本)。
- **移植坑(重要)**:官方 css 靠"等特异性+后写者胜"让 endOfContent 压在 span 之下;搬进 scoped 选择器后 span 规则多一层类、特异性反超,盾片盖住全部命中,**选择死在锚点**(0 字符)。修法=选择器补足特异性(`.pdf-text-layer > .pdf-end-of-content`)。教训入 L19。
- 实证(真实输入层):行内→左边距拖=该行前半 58 字符**单行单矩形**(标准"拖到边距选到行首");8 手势电池全绿;r3 8/8;PDF 19/19。已发 v12。测试侧附带发现:拖选出窗口会触发**选区自动滚动**污染读数(落点必须限窗口内);"anchor/focus 打印 className 为空"≠落在容器——**pdfjs 的 span 无类名**,诊断要以 getClientRects/几何为准。

### 2026-10-09 关窗行为修正:系统托盘(V1.5 §16 修正;WM_CLOSE 实证)

✕=隐藏到系统托盘(主任务栏不占位);托盘单击恢复;托盘右键菜单 Show/Exit(Exit=唯一真退出,app.exit→RunEvent::Exit→状态兜底)。实证:WM_CLOSE→窗口隐藏+进程存活 ✓;隐藏后二次启动恢复 ✓;退出状态落盘 ✓。托盘菜单 Exit 为纯 UI 入口(自动化不驱动,owner 复验;同源逻辑 show_main_window/app.exit 均已测)。

### 2026-10-02 关窗行为(V1.5 §16 修订;WM_CLOSE 真路径双验)

点 ✕=最小化到任务栏不退出;任务栏图标右键"关闭窗口"=真退出。区分规则=窗口是否已最小化(两种关闭请求系统层面同形)。实证:最小化+WM_CLOSE→退出+exit state 落盘 ✓;可见+WM_CLOSE→最小化+存活 ✓。已知差异:JS window.close() 在最小化窗口上不触发退出(Tauri 内部时序),用户路径(任务栏菜单=WM_CLOSE)不受影响。

### 2026-10-02 验收二轮(opener scope/I-beam/页签宽;PDF 19/19+P3 PASS)

① 右键 "Open with Default App" 一切文件报 `Not allowed to open path`——opener 双层门:capability 权限之外还有**插件 scope 白名单,默认空全拒**(lessons L16);修复=capabilities 带 scope(path:** ,URL 收紧 https/http)。**验证升级到真程序层:右键 notes.txt → 记事本弹出并打开文件(自动关闭)**;此前"无关联 .bin 报错 toast"只证 handler 执行,是盲区。② 查看器内容区 I-beam 光标(cursor:text)。③ 长文件名页签 160px 封顶+省略号,悬停 title 全名。

### 2026-10-02 验收轮返工(三项反馈;回归:修复 6/6+PDF 19/19+P3 PASS+P4 24/24)

① "点 PDF 没显示"=旧实例在跑(单实例激活旧窗,exe 本身实测正常),完全重启即好;② **引擎卸载策略改**(owner 拍板"关掉 PDF 页签引擎也要卸载"):每文档独立 worker+关最后页签 terminate——**连带修复 pdfjs destroy 连环哑炮**(先关 A 后 B 永挂 Loading,lessons L15);③ **全局文本不可选 bug**:body 的 user-select:none(Phase 1 壳层防误选)盖住了查看器,.viewer-body 恢复 text(txt/md/code 可划选复制;**PDF 画布选字=文本层功能,待 owner 表态**);④ 树右键 "Open with Default App" 点了没反应=L12 同族漏网(只修了页签菜单),快照先行修复(lessons L12 补记:按菜单族扫,不是修单个)。修复回归脚本 `%TEMP%\aiv-p5-fix-test.py`(选择断言 getSelection 非空;右键用无关联的 .bin 验证 handler 真执行→失败 toast,不弹真程序;worker 数开=1/关=0/重开=1)。

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
