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
- 🔴 **测试一律零前台**(owner 2026-01 立规,含"不许窗口闪现"):脚本不得 SetForegroundWindow/AppActivate/SW_RESTORE 抢焦点。**标准测法**(spec-003 起):
  `AIV_HIDDEN=1 AIV_TEST_PROJECT="<夹具路径>" WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222" <exe>` ——窗口全程不显示、项目自动添加(免原生选择框)、CDP/Playwright 驱动;正常双击启动不受影响(窗口由应用显式 show)。
  ⚠️ 隐藏窗口收不到可信键盘输入(CDP Input 层)——测应用 dispatcher 用 **DOM 合成 keydown**(window.dispatchEvent);物理键盘链路属 Phase 1 验证项,未变。拖拽用 Playwright mouse;截图用 PrintWindow 穿遮挡。旧法 SW_SHOWMINNOACTIVE 已废弃(启动瞬间仍会闪)。

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

**owner 验收建议路径**(1.5 分钟,release 已重建):双击桌面 AI Project Viewer → + 加 `Desktop\AIV-TestProject` → 展开一两层目录、右键 Pin 一个文件 → 开两三个文件页签 → ⚙ 改 Theme=Dark、字号 + 两次 → **完全关闭应用** → 再双击打开:项目标签、展开、置顶、页签(含激活页和 Rendered/Source 模式)、主题、字号应全部还原;点开恢复的页签内容正常显示(大文件不弹确认);关掉重开 Settings 确认两个开关还在。

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
