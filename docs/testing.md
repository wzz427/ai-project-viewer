# testing —— 测试唯一真值:怎么跑 · 怎么判过 · 历史账本

> 本文档 2026-10-10 应 owner 指令整体重写:此前是编年史(按时间堆记录)、
> 引用的脚本全在 `%TEMP%` 随系统清理蒸发。新结构:**§0–§3 是手册**(新 agent
> 只读这四节就能跑测试),**§4 起是历史账本**(证据链,别当手册读)。
> 所有现行脚本已入库 `scripts/e2e/`(含 README);PDF 专属知识见 docs/pdf-guide.md。
> Benchmark 档位定义见 V1.5 §162–§173;Phase 验收清单见 §188。
> **全量 Benchmark(A–I + Phase 1 Baseline 重跑)之前必须 owner 点头**(红线);
> 开发中秒级自测自己跑。

## 0. 档位速查

| 档 | 内容 | 何时跑 | 耗时量级 |
|---|---|---|---|
| T0 秒级自测 | `pnpm check` + `cargo test` + debug 构建启动冒烟 | 每次改动后 | <2 min |
| T1 Phase 功能自测 | §3 脚本清单按域跑(逐项实测留证据) | 每个 Phase 交付前 | 0.5–1 h |
| T2 Phase Baseline | §4.9(每 Phase 增量记录) | Phase 交付时 | ~10 min |
| T3 全量 Benchmark | V1.5 §166–§174 A–I 档(**脚本已建:`benchmark-suite.py`) | owner 批准后(V1 收口前) | ~1.5 h |

## 1. 环境与命令

### 1.1 命令速查

| 项 | 值 |
|---|---|
| 前端类型检查 | `pnpm check`(svelte-check,0 错 0 警为过) |
| Rust 单测 | `cd src-tauri && cargo test` |
| 前端单测 | `npx vitest run` |
| release 构建(GUI 测试用) | `pnpm tauri build --no-bundle` → `src-tauri/target/release/ai-project-viewer.exe` |
| e2e 解释器 | **conda pywork**:`C:\Users\wzzpk\.conda\envs\pywork\python.exe`(owner 指定;Playwright/reportlab/pypdf/psutil 已装) |
| ⚠️ 网络前置 | npmjs 直连不通,仓库 `.npmrc` 已固定 npmmirror;cargo 走 crates.io 直连可通 |

### 1.2 夹具

**桌面 `AIV-TestProject`**(owner 指定建,31 文件:md/json/yaml/toml/txt/csv/log/py/ts/rs/css/html/sql/ps1/bat + 图片五格式 + edge-cases[GB18030/UTF-16BOM/UTF-8BOM/二进制/5MB/21MB],两层嵌套,含内嵌脚本的安全 SVG)。owner 验收直接用它。
PDF 夹具**丢失/损坏时重建**:`pywork python scripts\e2e\make-fixtures.py --force`
(生成 10 页文本/100 页文本/100 页扫描[~14MB 现规格]/tab-1..5;行文本模式是断言依据,勿改)。

## 2. GUI 测试规程(正典;owner 2026-10-09 立规"不许抢鼠标、不许弹窗")

### 2.1 零打扰启动公式(scripts/e2e 全部脚本已内置)

```
AIV_HIDDEN=1
AIV_TEST_PROJECT=<夹具路径>            # 免原生选择框,自动加项目
AIV_STATE_FILE=%TEMP%\<独立>.json      # 永不碰真实 state(闸门)
WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=<port>
<release exe>
```

⚠️ **隐藏窗口的定时器是停摆的**(lessons L28):AIV_HIDDEN 下页面 setTimeout 不触发,直到一次输入事件;断言依赖防抖/延时的逻辑要么走直取路径,要么先发一次输入唤醒。IPC 往返不受影响。

窗口隐藏启动后 **SetWindowPos 移屏幕外(-2500)+SW_SHOWNOACTIVATE**——保持渲染
(最小化窗口的 caretRangeFromPoint/hit-test 读到过期布局,屏幕外才准),全程不可见、
不抢前台;正常双击启动不受影响。隐藏窗口收不到可信键盘输入(CDP Input 层)——测应用
dispatcher 用 **DOM 合成 keydown**(window.dispatchEvent);物理键盘链路属 owner 复验项。

### 2.2 输入分层(下药前先分层)

| 层 | 方法 | 测什么 |
|---|---|---|
| 页面内派发 | JS `new MouseEvent/PointerEvent` dispatch 到目标元素/window | **我们自己的 DOM 逻辑**(如 PDF 选择驱动)的完整路径;绕开可信合成的坑 |
| 可信 CDP | Playwright connect_over_cdp 的 mouse/keyboard | 原生路径、且场景中 JS 不写选区时;**盲区:JS 写过选区后,拖动中的可信 move 会被浏览器吞** |
| 真实输入层 | Win32 SetCursorPos/mouse_event;**坐标自校准 `屏幕=ClientToScreen 原点+CSS×(客户区宽/innerWidth)`**(别乘 dpr——DPI 虚拟化下错 1.25 倍);**手势前必查 GetForegroundWindow**,丢了就点击自家未被遮挡区带回(WindowFromPoint 探测可见点;拖标题栏会变成拖窗口) | 仅 owner 明确许可占用鼠标时,或最终交叉验收 |
| 官方 oracle | `scripts/e2e/oracle/oracle.html`(官方完整查看器驱动页,搭建见 e2e README) | 判定"我们的问题还是上游/内核"——动代码前先拿它定基线 |

辅助手段:`Emulation.setDeviceMetricsOverride`(deviceScaleFactor=1.25=owner 实测
AppliedDPI 120 / width=1536 模拟最大化)用于一切几何断言与宽屏场景。

### 2.3 铁律

1. **场景必须复刻 owner 原话手势**(窗口是否最大化、出界方向、按住移动路径)——历史上三轮假"修好了"全栽在场景不对齐;
2. 疑内核问题**先查 `navigator.userAgent` 的 WebView2 版本**(143 有选择内核缺陷、155 修好;升级=离线包以管理员运行 `/silent /install`,引导器/winget 静默装对 per-machine 报 0x80040828);
3. **断言写进脚本自判 PASS/FAIL**,不留人工判读;
4. **合成输入 ≠ 真实输入**(lessons L17)——合成只证 handler 逻辑;交付口径以 owner 亲手复验为准;
5. **禁止**向"当前前台窗口"盲发按键(SendKeys 落进宿主终端;必须先 GetForegroundWindow 校验,lessons L3);禁止 SetForegroundWindow/AppActivate/SW_RESTORE 抢焦点。

## 3. 脚本清单(scripts/e2e/,2026-10-10 全量入库)

跑法与前置详见 `scripts/e2e/README.md`。全部自带零打扰启动,release 构建后直接跑。
**隔离红线(2026-10-10 owner 立规,实现在 `aivlaunch.py`)**:零打扰 = 不抢前台 + **不杀 owner 的进程**(绝不按进程名杀,只 PID/构建树路径限定)+ **不碰 owner 的窗口**(绝不按标题找窗,只按 PID)。所有脚本的启动/清理必须走 `aivlaunch`。

| 脚本 | 覆盖 | 何时跑 |
|---|---|---|
| `pdf-selection-battery.py` | PDF 文本选择全场景(V1–V8:拖选/边距出界/按住空白上下移动[反选原场景]/行首垫起选/跨页/串台污染/宽屏右出界/双击) | 凡动 PdfViewer/文本层/选择驱动 |
| `pdf-suite.py` | PDF 功能 19 项:渲染/翻页/缩放/fit/搜索/虚拟化/释放/恢复/扫描件 | 凡动 PDF 相关 |
| `phase3-suite.py` | 查看器+移交+树交互回归 **88 项**:MD/代码/JSON/图片/页签/编码/快捷键/工具栏 + Phase 6 三右键菜单分型/复制 toast/两端同源/VS Code Mode 持久化 + Phase 8:Run 菜单矩阵(ps1/py/exe/msi)/exe 信息卡/未信任自动取消/项目菜单 Refresh+Trust 翻转/失败弹窗+底部右键钳制守卫(script/exe/project 每按钮在视口内,0.6.10 增) + **Phase 9 监听:树自动增删/激活页签自动重读+§82 toast(双写合并一次)/删除态+Close Tab/改名跟随页签与置顶(watcher_×5,外部写盘全程零手势)** + **0.7.4 行号对齐守卫:连按 A+ 六档后全行 行号-正文 偏差<1px+行号字号跟随正文** + **0.7.6 opener 授权守卫(p10_×2):渲染层直调 plugin:opener|open_path 与 open_url file:// 必须双拒(断言 rejection,不弹任何窗口)** + **0.7.7 工具栏防选中守卫:双击+三连击 A+ 后 selection 必空(L40)** + 0.7.9 右键动作保高亮 + **0.7.11 内容身份守卫×2(data-rel==激活页签文件+正文新旧互斥;冻结大案的守卫缺口——此前全部断言只查页签名+类名,不查内容身份)** + **0.7.22 页签批量关闭守卫(×8):左清/右清/其他清的幸存集+置顶豁免+锚点接管激活+无对象侧禁用态** + **0.7.23 纸感守卫(×7):暖纸底双主题/15px 提升/88ch 限宽居中(行宽闸改判新契约)/衬线标题/赭石链接/自绘复选框/hljs token** + **0.8.0 chrome 守卫(×3):三层阶梯三值互异/项目激活零线条/文件激活单发丝线;light_viewer_white 改判 light_viewer_paper** | 凡动查看器、页签、右键菜单、handoffMenu/run.rs/trust/watcher 链/CodeViewer 字号路径/**capabilities 授权** |
| `git-suite.py` | Phase 7 Git 检视 33 项:三实例(BigRepo 根=正常/apps\viewer=子目录 §174/AIV-TestProject=非 Git)——徽标计数/页签 ●✓/树标记字母/面板分组/点击开 diff(wt+staged)/同文件双组单计/超限守卫/手动刷新 + 0.6.8 返修:并排 diff 双侧断言/Git 视图期间隐藏文件页签/name+dir+letter 分段排版/提交时间单位/提交详情钻取→提交视角 diff→返回与关闭 + **Phase 9:外部写/删探针→徽标自动 [8]/[7](零手势,V5;窗口 park offscreen——L34)**;夹具每次在 %TEMP%\aiv-p7-gitscope 重建 | 凡动 git.rs/GitPanel/gitStore/徽标/树标记/DiffViewer/CommitDetailView/diffSideBySide/App 模式切换/watcher→git 链 |
| `recent-suite.py` | Open Recent **15 项**(0.7.3,spec-010):预置状态文件+AIV_TEST_PROJECT 自动加两路驱动(原生选框绝不驱动,D4)——记录+MRU+cap 挤旧/菜单结构(Browse 首项+Clear 底部)/失效置灰+报错/打开新项目与切换已开/Esc 关闭/重启持久化/行内✕与 Clear 落盘/空白欢迎页列表;夹具 %TEMP%iv-p10-recent 每次重建;**Clear 之后严禁再点 +(空表会弹原生选框)** | 凡动 recentStore/AddProjectMenu/EmptyState/appState recentFolders 字段 |
| `acceptance-r3.py` | 验收轮 8 项:更新按钮位置/MD 任务清单/右键 Copy/文本层 | UI 通用改动 |
| `real-input-battery.py` | 真实鼠标 8 手势电池(app+官方 oracle 双模式,前台守卫) | **仅 owner 明确许可占用鼠标时** |
| `run-live-check.py` | **手动专用**(会开真控制台窗):Phase 8 运行真机检——信任菜单翻转→Run Script→WindowsTerminal 控制台出现+脚本体执行+结束后驻留;系统级窗口差集归因(Win11 默认终端宿主不在 app 子树) | 动 run.rs/信任门时手跑一次;**绝不入例行轮** |
| `watcher-freeze-guard.py` | 监听抗冻守卫(0.7.0 启动卡死教训,L35):%TEMP% 夹具(300 文件/30 提交 git 仓)+持续写盘锤击(改写+增删 ~33 周期/秒)25s,`SendMessageTimeout(WM_NULL)` 测**原生窗口线程**(渲染进程健康≠窗口没冻);PASS=无响应采样≤2 | **凡动 watcher 链/git_snapshot/事件刷新路径,发版前必跑** |
| `benchmark-suite.py` | **T3 全量基准**(A–I+Phase 1 Baseline 重跑,V1.5 §161–§174):A 壳启动/RAM/CPU(双口径:隐藏=下限+`show_main_offscreen`=真实,L42)·B 常规页签/切换·C 多项目预置恢复·D node_modules>10 万文件·E Agent 锤击 60s·F/G PDF RAM 增量·H 大 diff 截断·I=复跑 git-suite;psutil 全进程树**私有字节**口径(§161);结果落 %TEMP%\aiv-bench\results.json | T3 轮(owner 批准后);性能回归疑点复测 |
| `freeze-repro.py` | **冻结大案复现器**(v4):4 项目/开机激活≠列表首位/先健康两切/三连快切(1.2s)+10s+切嵌套项目+0.8s 连点+扩散期;每步断言**内容身份**(data-rel+marker);2026-10-12 战绩:v3 配方第 0 轮命中一次(页签条+viewer 同死),其余 96 轮活(≈2%) | 冻结大案再现时先跑;凡动 ActiveViewer/tabsStore 激活路径/项目切换 |
| `freeze-probe.py` | 冻结**解剖器**:循环配方直至冻结,活体解剖(JS 直发点击/项目往返 store 真值读回/控制台全收);`FREEZE_PROBE_EXE`+`FREEZE_PROBE_FAST=1` 支持 A/B 与放大 | 冻结命中后的分层定位 |
| `live-inspect.py` | **活体直连**(owner 2026-10-12 指令):只读附身正在运行的实例(常开端口 9322),调 `window.__aiv.snapshot()` 吐项目/页签/DOM 三对照/日志环;**绝不 launch/kill/focus** | owner 客户端任何异常现场的第一动作;0.7.12 起有效 |
| `visual-check-014.py` | spec-014 视觉自检:双主题 7 张截图(offscreen 显示窗口 CDP 出图,L42 口径);截图供人眼/视觉模型终审+像素抽样核染色层 | 凡动主题 tokens/图标体系/两级标签样式 |
| `make-fixtures.py` | 重建 PDF 夹具(见 §1.2)+ handoff 夹具(example.url/demo.exe,缺时才创建) | 夹具丢失/损坏时 |
| `oracle/` | 官方查看器对照基准(搭建见 README) | 疑上游问题 |

**已蒸发的历史基建**(原 `%TEMP%` 的 aiv-cdp.mjs/aiv-picker.ps1/aiv-confirm.ps1/aiv-shot.ps1,
2026-10-10 盘点时已被系统清理):CDP 注入→现由 e2e 脚本的 Playwright over CDP 覆盖;
原生对话框驱动(picker/confirm)→现行脚本用 AIV_TEST_PROJECT 免选择框 + test_mode_active
自动应答,如需驱动原生对话框按 lessons L7(UIA+Win32 消息按 ClassName 找控件)重建;
穿透遮挡截图(PrintWindow PW_RENDERFULLCONTENT)→按同名 API 重建,约 15 行 PowerShell。

---

## 4. 历史账本(append-only;证据链,**不是手册**)

> 各 Phase/轮次的实测记录与数字判读。开头统一声明:**本区引用的旧 `%TEMP%` 脚本名是
> 当时名**——现行对应见 §3;未入库者(标注"未存档")其断言清单即重建规格。
> 现行回归一律跑 §3 清单,不在本区找命令。

### 4.10 Phase 7 Git Review(2026-10-10,spec-007;全部通过)

| 档 | 结果 |
|---|---|
| cargo | **76/76**(git.rs 新 13:porcelain v2 解析/renamed TAB 实证/§174 子目录 scope/ahead-behind 真克隆/冲突 U 双组/diff 守卫截断/空仓+detached/非 Git/路径消毒/安全旗标) |
| vitest | **25/25**(gitFormat 新 6:badgeText 0/99+/relativeTime 各档/marksByRel staged 优先) |
| svelte-check | 0 错 0 警 |
| git-suite | **24/24**(见 §3 行;含 owner 可见路径:↻ 后徽标 7→8→7 往返) |
| phase3-suite | 44/44 防退化 |
| acceptance-r3 | 8/8 |
| pdf-suite | 19/19 |
| 版本 | 0.6.7 三处已核 |

#### 0.6.8 返修轮(2026-10-10,owner 0.6.7 复验三反馈;全部通过)

| 档 | 结果 |
|---|---|
| cargo | **77/77**(+1 parse_commit_detail:改名/作者/文件;log 解析补 author 字段) |
| vitest | **33/33**(+8 diffSideBySide:分段/拉链对齐/折叠计数/路径提取) |
| svelte-check | 0 错 0 警 |
| git-suite | **30/30**(+6:side_by_side 双侧/hides_file_tabs/name_dir_letter_split/commit_time_unit_fixed/commit_detail_drill/commit_diff_back_close) |
| phase3-suite | 44/44 防退化 |
| acceptance-r3 | 8/8 |
| pdf-suite | 19/19 |
| 截图自评 | 面板+并排各一张(视觉工具核:分段/计数徽章/提交图形列/HEAD 胶囊/行对齐/折叠条落地,时间 "1m ago") |
| 版本 | 0.6.8 三处已核 |

### 4.11 Phase 8 RUN/Trust(2026-10-10,spec-008;全部通过)

| 档 | 结果 |
|---|---|
| cargo | **86/86**(run.rs 新 8:argv 无 -ExecutionPolicy/cmd /K 构型/白名单拒绝/越界拒绝/两宿主存活性[stdin 持管法];handoff +1:.url 禁协议接线) |
| vitest | **39/39**(menuKind 新 5:script 三扩展/py-js-sh 排除/exe-msi 分裂/大小写/folder-browserText;appState +1 trust 往返+旧态无字段愈合 false) |
| svelte-check | 0 错 0 警 |
| phase3-suite | **54/54**(+10:见 §3 行;untrusted 自动取消走 test_mode_active 分支,零打扰红线保住) |
| git-suite | 31/31 防退化 |
| acceptance-r3 | 8/8 |
| pdf-suite | 19/19 |
| run-live-check(手动真机) | **PASS**:信任菜单翻转→Run Script→WindowsTerminal 控制台窗出现→脚本体执行(marker)→结束后 2.5s 仍驻留 |
| 版本 | 0.6.9 三处已核 |

#### 0.6.10 返修轮(2026-10-10 晚,owner 指令:新菜单项加入后底部右键必须仍完整显示;全部通过)

| 档 | 结果 |
|---|---|
| 现状实证 | 五种菜单底部右键(script 8 项/exe/msi/textLike/project)全部落位视口内——钳制逻辑量实际高度自适应,无需改产品代码 |
| phase3-suite | **56/56**(+3:menu_clamped_bottom_script/exe/project——断言从"菜单容器在视口内"加码到"**每个按钮**都在视口内") |
| 其余档 | git-suite 31/31+r3 8/8+pdf 19/19+vitest 39/39+check 0/0(无代码变更,防退化) |
| 版本 | 0.6.10 三处已核 |

#### 0.6.11 返修轮(2026-10-10 深夜,owner 报障:切回 Files 页签丢失;全部通过)

| 档 | 结果 |
|---|---|
| 根因 | git 视图(Phase 7 单槽)寿命未绑定面板:setSidebarMode 只翻模式不关视图,切回 Files 后 FileTabs 仍被 `{#if}` 藏着、主区仍被 diff 占着;页签数据未丢(lessons L31) |
| 修法 | setSidebarMode 离开 git 即 closeGitView + activateProject 切项目即 closeGitView(同族隐患:跨项目残留) |
| git-suite | **32/32**(+1:git_return_to_files_restores_tabs=owner 原流程复现:开页签→Git 点条目→回 Files→页签+激活页+内容回来) |
| 其余档 | phase3 56/56+r3 8/8+pdf 19/19+vitest 39/39+cargo 86/86+check 0/0 |
| 版本 | 0.6.11 三处已核 |

#### 0.6.12 返修轮(2026-10-11,owner 两 bug+诊断能力;全部通过)

| 档 | 结果 |
|---|---|
| 树右键高亮 | contextMenuTarget 瞬态独占(NodeContextMenu 挂载设/卸载清);phase3 +1 right_click_row_owns_highlight |
| demo.exe 夹具 | 假 PE(535B)→rustc 编译真程序(打印+回车退出);make-fixtures 重建,产品路径真机 launch+toast 实证 ✓ |
| 信任 toast 文案 | $derived 先写后读翻案(lessons L32);phase3 p8_trust_toggle 断言加硬到分支词 |
| 诊断导出(新) | 日志环(600 条:全局错误+boot/tab/project/git/viewer 事件)+Settings Export Diagnostics(含 live-check 页签↔主区对照+项目/页签状态+日志)→app_config_dir/diagnostics/*.txt;phase3 +1 diagnostics_export_writes_report |
| 全档 | phase3 58/58+git-suite 32/32+r3 8/8+pdf 19/19+vitest 39/39+cargo 86/86+check 0/0 |
| 版本 | 0.6.12 三处已核 |

#### 0.6.13 返修轮(2026-10-11,owner 两反馈;全部通过)

| 档 | 结果 |
|---|---|
| Run 反馈重做 | 成功无提示;失败=窗口正中 ErrorDialog(标题+原因,Esc/OK 关);phase3 p8_launch_failure_dialog(居中几何±4px+Not found 原因+无 toast+关闭) |
| 诊断区清理 | Settings 只留 Export 按钮;导出路径改由 toast 呈现(e2e 同步改);读数仍进报告 |
| 全档 | phase3 58/58+git 32/32+r3 8/8+pdf 19/19+vitest 39/39+cargo 86/86+check 0/0 |
| 版本 | 0.6.13 三处已核 |

实现期两教训(lessons L29/L30):release GUI 构建必须 `pnpm tauri build --no-bundle`(plain cargo build 缺 custom-protocol,页面 ERR_CONNECTION_REFUSED);Win11 默认终端=WindowsTerminal.exe,控制台窗不在 spawn 者进程树内,检测须系统级差集。

#### 0.7.0 Phase 9 Watcher 首发轮(2026-10-11,spec-009;全部通过)

| 档 | 结果 |
|---|---|
| cargo | **95/95**(watcher.rs 新 9:§32 忽略段过滤/rel 计算/相邻配对+不焊幻影 rename/storm 折叠/classify 全形状+**Windows Name(Both) 拆分**/真监听冒烟=tempdir 写文件批到达+忽略目录不跨 IPC) |
| vitest | **50/50**(watcherApply 新 11:needsReload 精确路径不含祖先/isGone 含目录前缀+rename from/renamedRel 文件+祖先目录+不匹配前缀) |
| svelte-check | 0 错 0 警 |
| phase3-suite | **63/63**(+5:watcher_tree_auto_add/auto_remove、watcher_active_file_auto_reload[双写 400ms 内合并一次 reload+一次 toast]、watcher_deleted_tab_state[删除态+Close Tab 真关]、watcher_rename_follows_tab[标题+active+pin+内容]) |
| git-suite | **33/33**(+1:git_watcher_auto_refresh_updates_badge——外部写/删探针,徽标自动 [8]→[7] 零手势;套件补 park_offscreen) |
| acceptance-r3 | 8/8 |
| pdf-suite | 19/19 |
| 版本 | 0.7.0 三处已核(package.json/tauri.conf.json/Cargo.toml) |

实现期两教训(lessons L33/L34):Windows 上 notify 的 rename 是**单个 Name(Both) 事件带 [from,to]**,按 From/To 两事件的心智模型写分类器必漏(树靠重列兜底掩盖根因,页签不跟才暴露);隐藏 WebView2 冻结的是定时器队列不是页面——fs 事件照常送达 handleBatch,但其中 refreshGit 的 400ms 防抖定时器冻着(git-suite 徽标涨不回落;诊断环两笔 fs-change 都在+零报错定位)。修=watcher 触发的 git 刷新走 refreshGitNow 直取(Rust 侧已合并过,前端无需二次防抖)+e2e 一律 park_offscreen。

#### 0.7.1 返修轮(2026-10-11,owner 报"一打开就卡死,点击全是 ⌛️";全部通过)

| 档 | 结果 |
|---|---|
| 根因 | **同步命令跑在原生主线程**(L35):git_snapshot(起 git.exe,真仓库 0.1–2s)被监听变成每事件批次触发,AI 会话持续写盘时主线程被占死不泵消息——小夹具 e2e 测不出(单批仅几十 ms) |
| 修复 | ①git_snapshot → async 命令+spawn_blocking(离主线程,聚焦/手动刷新的隐性卡顿一并消除)②watcherStore 单 lane 串行+忙时合并批次(防堆积,无 setTimeout——L34) |
| **watcher-freeze-guard** | 复现:持续锤击(改写+增删 ~33 周期/秒)下原生窗口 40 采样 **29 个无响应**(SendMessageTimeout WM_NULL;渲染进程当时 18ms"健康"——测错了对象);修复后 **0/83 + 渲染 10ms,PASS** |
| 全档 | phase3 63/63+git-suite 33/33+r3 8/8+pdf 19/19+vitest 50/50+cargo 95/95+check 0/0 |
| 版本 | 0.7.1 三处已核 |

#### 0.7.2 返修二轮(2026-10-11,owner"0.7.1 换装后仍启动即卡死";全部通过)

| 档 | 结果 |
|---|---|
| 根因 | **第二层独立根因(L36)**:notify-debouncer-full Windows 默认 FileIdMap,watch() 里对项目根全树 WalkDir+逐文件开句柄——真实仓库分钟级;start_project_watch 同步命令=主线程 → 冻死。小夹具毫秒级 → e2e 全绿放行 |
| 修复 | `new_debouncer_opt+NoCache`(改名配对用路径 From/To,文件 ID 缓存白付)+start/stop 全转异步+spawn_blocking |
| 真实状态验证 | owner 状态副本:修前 **75/75 无响应(CPU 满核)** → 修后 **0/75+CPU 0.4s**;bisect=禁用监听构建 0/50 一锤定音 |
| 全档 | phase3 63/63+git-suite 33/33+r3 8/8+pdf 19/19+vitest 50/50+cargo 95/95+check 0/0+freeze-guard 0/83 |
| 版本 | 0.7.2 三处已核 |

#### 0.7.3 Open Recent 首发轮(2026-10-11,spec-010;全部通过)

| 档 | 结果 |
|---|---|
| recent-suite | **15/15**(记录+MRU/cap 挤旧/菜单结构/失效置灰+报错/打开与切换/Esc/重启持久化/✕+Clear 落盘/空白页列表) |
| 全档 | phase3 63/63+git 33/33+r3 8/8+pdf 19/19+vitest **60/60**(recentList 10 新+appState recentFolders 2 新)+cargo **96/96**(paths_exist 新)+check 0/0;freeze-guard 免跑(watcher 链零改动) |
| 发版后核验 | 三处版本 0.7.3;三二进制:target\release=**dev 标识**✓、target-exp 与 updates=**exp 标识**✓——**标识字节在 4MB 窗口外,须全文件扫**(连带修了 swap-experience-client.py 的同款窗口误判) |

#### 0.7.4 行号错位返修轮(2026-10-11,owner 截图报障"行标号和行字符串没有对齐";全部通过)

| 档 | 结果 |
|---|---|
| 根因 | 全局字号走 :root CSS 变量,CodeMirror 看不见非自己施加的样式变化→缓存行高过期→**行号列(高度按旧测量显式指定)逐行漂移**;探针实证:14→20px 十二行文件偏 100px,滚动/内容溢出才偶然触发重测自愈。默认 13px 时偏移不可见——0.6 工具栏(SPEC-INFRA-003)起潜伏,owner 调大字号后显形。**非 0.7.x 引入** |
| 修复 | 字号一变即**重建**编辑器实例(watcher contentRev 重挂载同款确定性模式,§160.5 保滚动);行号随正文同字号(VS Code 行为)。弃 requestMeasure/内部 measure 路线:离屏窗 RAF 节流+行号刷新依赖 update 旗标,探针实证不愈(12 行短文件 92px 不动) |
| 全档 | phase3 **64/64**(+gutter_aligned_across_font_changes)+git 33/33+r3 8/8+pdf 19/19+recent 15/15+vitest 60/60+cargo 96/96+check 0/0 |
| 版本 | 0.7.4 三处已核;发版后三二进制全文件扫描:updates=exp 0.7.4✓、dev 完好(标识 dev);dev 构建同日重至 0.7.4 |

#### 0.7.5 字号上限轮(2026-10-11,owner"字体怎么最大加到20px就到头了";全部通过)

| 档 | 结果 |
|---|---|
| 变更 | 上限 20→**32px**(下限 11/默认 13 不变);范围收成 appState 导出 FONT_SIZE_MIN/MAX 单一常量,setFontSize 与解析自愈共用 |
| 验证 | 探针:13px 连按 25 次 A+ 到顶 **32px**,行号同字号且对齐 0 偏差;vitest 60/60(钳制 99→32)+check 0/0+phase3 64/64+r3 8/8 |
| 版本 | 0.7.5 三处已核;updates=exp 0.7.5(全文件扫)、dev=dev 标识 0.7.5 |

#### 0.7.6 Phase 10 上线前体检轮(2026-10-11,spec-011;全部通过)

| 档 | 结果 |
|---|---|
| 审计 | §184 九泄漏+十一风险逐项留证(住 SPEC §四审计表):净 14/按设计 1/特性 1/**漏已修 3+主线程 2**;一次性探针 V3(DOM 30 轮开关节点数 105→105 零增长)/V4(会话结束零孤儿,按 target 构建树+fixture 引用限定——**进程名过滤须限定构建树**,owner 体验版客户端同名共存) |
| 修复 | ①git show 两处补 --no-ext-diff/--no-textconv(§70)②cmd /K 路径 raw_arg 双层引号(探针实证:单层引号下 `a&calc&` 文件夹注入跑出 calc=注入成立活证据;**测试纪律:注入类真 spawn 测试的载荷命令必须选无害命令**,本轮 calc 弹窗已清理)③opener 授权收紧(删 allow-open-path **+opener:default,只留 open_url http/https;插件文档证实 scope 仅 IPC 层,Rust 自由函数不受影响)④git_diff/git_commit_detail+inspect/read_text/read_media/read_binary 六命令全转 async+spawn_blocking(L35 泛化) |
| cargo | **99/99**(+3:show_diff_argv 旗标/cmd 元字符单元/& 文件夹真 spawn 注入回归) |
| vitest | 60/60(无前端逻辑变更,防退化) |
| svelte-check | 0 错 0 警 |
| phase3-suite | **66/66**(+2:p10_opener_open_path_denied/p10_opener_file_url_denied——渲染层直调插件 IPC 断言拒绝) |
| git-suite | 33/33(命令转 async 后全绿=行为不变) |
| recent/r3/pdf | 15/15、8/8、19/19 |
| freeze-guard | **0/82 + webview 11ms PASS**(动了 watcher→git 链,必跑档) |
| 版本 | 0.7.6 三处已核 |

#### 0.7.7 工具栏按钮变蓝返修轮(2026-10-11,owner 截图报障"点击字体放大缩小…按钮显示蓝色";全部通过)

| 档 | 结果 |
|---|---|
| 根因 | 连点 A+/A− 落进双击窗口时,浏览器按词选中按钮标签("A+"/"+"),原生 ::selection 蓝色高亮挂在按钮上("有时"=节奏);**L40**——`.viewer-body user-select:text` 罩住工具栏,Chromium 对 button 文字默认不豁免 |
| 修复 | 全局 `button{user-select:none}`+两工具栏容器(.vtb/.toolbar)none+容器内 input 显式恢复 text(继承属性会罩坏输入框选词) |
| 验证 | 探针复刻:修前双击 selection='+' 199 蓝像素/三连击 'A+\n' 343 → 修后全空/19(基线);phase3 新守卫 `toolbar_buttons_not_selectable`(双击+三连击后 selection 必空) |
| 全档 | phase3 **67/67**(+1)+pdf 19/19+r3 8/8+vitest 60/60+check 0/0+cargo 99/99 |
| 版本 | 0.7.7 三处已核 |

#### 0.7.8 code review 修复批(2026-10-11,spec-012;全部通过)

| 档 | 结果 |
|---|---|
| cargo | **112/112**(+13:H1 多行消息[%B 尾 %x1e 分隔,夹具须 `--cleanup=verbatim`——git 默认剥行尾空白]/M2 merge first-parent[L-f12 族旗标断言同步]/L-r2 unquote 全转义集/L-r3 :(literal) pathspec[Windows 禁 `*` 用 `[xy]` 探]/L-r6/L-r1/M6 stderr 洪水[autocrlf 1500 文件不误报超时]/H2 decide 纯函数/M5 截断 BOM 样本/M11 拒绝表+msi 豁免/L-r5 % 路径拒绝/M4 代次自弃×2[真 debouncer 双 tempdir]) |
| vitest | **64/64**(+4:watcherApply 链式改名不动点/环上限) |
| svelte-check | 0 错 0 警 |
| phase3-suite | 67/67 防退化 |
| git-suite | 33/33(15 命令 async+gitStore 单飞后全绿;merge 提交详情现走 first-parent unified) |
| recent/r3 | 15/15、8/8 |
| pdf-suite | **23/23**(+4:M8 搜索中切页签零 pageerror+中断后复搜可用/M9 快切回位置比例还原 ±0.02[断言按文档占比,页缝 16px 使逐页算法不可靠]/M7 缩放风暴 settle 后每页恰一 canvas 同一 scale) |
| freeze-guard | **0/83 + webview 14ms PASS**(动了 watcher 链,必跑档) |
| 版本 | 0.7.8 三处已核;updates=exp 0.7.8(VERSIONINFO 核,字串扫描对 PE 无效) |
| 教训重演 | **L29 当日重演一次**:warning 清理用了裸 `cargo build --release` 覆盖 tauri 产物→e2e 全线白屏(ERR_CONNECTION_REFUSED);双构建重建走 `pnpm tauri build --no-bundle [--debug]` 后全绿——**GUI 二进制永远只认 tauri CLI 产物** |
| 记档延后 | L-c6 noUncheckedIndexedAccess 实测 60 错/8 文件>D6 止损线 20,回退记档(spec-012 D12;去处=下一前端专项批次) |

#### 0.7.9 高亮返修轮(2026-10-12,spec-012 InTest 期间 owner 报障;全部通过)

| 档 | 结果 |
|---|---|
| 根因 | 树高亮单一真值=激活页签(2026-10-10 规矩)×右键瞬态独占(0.6.12)⇒ 菜单一关高亮还给旧激活文件;探针五步实证无点击穿透、非 0.7.8 引入(L41) |
| 修复 | 动作过的行保持高亮(acted 标记,动作关闭不清);dismiss 照旧回落;下次文件激活(revealInTree 咽喉)交还;forgetTree 同步清 |
| phase3-suite | **68/68**(+1 `context_action_keeps_row_highlight`;载荷=Copy-Path 非 reveal——零打扰红线) |
| 其余档 | git 33+recent 15+r3 8+pdf 23+cargo 112+vitest 64+check 0/0(watcher 链零改动,freeze-guard 免跑) |
| 版本 | 0.7.9 三处已核;updates=exp 已发 |

#### 0.7.10 前端索引访问收紧轮(2026-10-12,spec-013;全部通过)

| 档 | 结果 |
|---|---|
| 变更 | tsconfig 开 noUncheckedIndexedAccess **常开**;60 处见底——产线 22(守卫/结构改写,归型清单住 SPEC §六)+测试 38(显式断言,D1-C);零行为变化 |
| check | **0 错 0 警**(开关开) |
| vitest | 64/64(仅类型层改动,防退化) |
| phase3/git/recent/r3/pdf | 68/68、33/33、15/15、8/8、23/23 |
| cargo/freeze-guard | 免跑(Rust 零改动;8 文件与 watcher 链零交集,spec-013 D2) |
| 版本 | 0.7.10 三处已核;updates=exp 0.7.10(UTF-16 VERSIONINFO 核,无 0.7.9 残留) |

#### 0.8.0 墨与纸·全套界面统一(2026-10-14,owner 报障树不和谐+双蓝线相撞+两栏无层次,demo 三选 C+层次加强+代码面同纸;全部通过)

| 档 | 结果 |
|---|---|
| 诊断 | 双蓝线相撞=项目标签激活 inset 0 -2px(向下)×文件标签 ::after top -3px(向上)横向靠近必叠;两栏底色仅差一档灰且侧栏与文件栏同色;0.7.23 后文档暖纸×chrome 冷灰=一窗两温 |
| 实现 | app.css 令牌整体换血(墨与纸):**三层阶梯** band(--bg 暗 #100e0b/亮 #e2dbcc,首次加深一档不够,视觉评审后二次加深)→ frame(--bg-raised #26221b/#f2eee5=侧栏+文件栏)→ paper(--viewer-bg #211f1c/#faf8f4=全部阅读面);**强调色蓝→赭石**(与文档链接同族,demo C;accent/accent-soft/accent-strong 全换,Git 字母/--danger 功能色不动);**项目标签去线**(激活=填充芯片+加粗,0.8.0 C 决定——底边线与文件标签顶边线的相撞在结构上消失);文件标签保留唯一一根顶边发丝线;选区高亮 ::selection 暖色 30% accent;MarkdownViewer 的 bg/text/link/border 令牌接全局防漂。**代码/文本/JSON 查看面同纸**(owner 拍板,--viewer-bg 即纸) |
| 对比度 | 阶梯全对 AA 脚本过秤:亮 band 文字 4.86/强调 4.62(#e2dbcc 档,首轮 #e7e1d4 双 FAIL 调深)、frame 4.96+、纸面 14+;暗 band 6.9+/frame 5.7+/纸 11.4;白字@accent-strong 暗 5.28/亮 6.37 |
| 全档 | vitest 90/90+构建过+phase3 **88/88**(+3 chrome 守卫:三层阶梯三值互异+项目激活零线条+文件激活单发丝线 2px 赭石;**light_viewer_white 旧闸改判 light_viewer_paper**——0.7.x『亮色阅读面=纯白』契约被 0.8.0 全套纸取代);实拍双主题+视觉评审确认(层次分明/语义清晰/色温统一) |
| 版本 | **0.8.0**(owner 指示升段,2026-10-14;0.7.x 递增纪律就此翻页)三处已核;updates=exp 0.8.0(15:14,UTF-16 核:0.8.0 FOUND/0.7.23 absent,拒发闸 staged 0.7.23→publishing 0.8.0);owner 路径=Update→重启→双主题看整体;两个 demo 文件验收后可删 |

#### 0.7.23 Markdown 纸感编辑部改版(2026-10-13,owner demo 三选:C 方向+88ch 限宽+语法着色;全部通过)

| 档 | 结果 |
|---|---|
| 调研 | 计算样式取证:正文 13px(外壳小字漏进阅读面)/标题与正文同色梯度弱(H1 仅 20.8px)/链接裸 UA 蓝 rgb(0,0,238)/引用灰字灰边/块级元素无节奏;桌面 demo(AIV-MD渲染对比-demo.html)四方案双主题+行宽开关交 owner 实判 |
| 实现 | MarkdownViewer 渲染态换「纸感编辑部」令牌(scoped,不进 app.css——外壳/代码面保持 spec-014 冷灰界,温度切换是渲染↔源码的模式信号):暖纸底/墨字/衬线标题(拉丁 Georgia+中文黑体)/赭石链接(45% 下划线,悬停加深)/编辑部表格(粗横线无竖线+淡斑马)/❧ 分隔线/自绘任务复选框(勾选行退灰);正文 calc(旋钮+2px)=默认 15px;.prose 88ch 限宽居中(**推翻 2026-10-10 不限宽——当年拒的是冷底空白带,新方案纸底铺满无冷带**);**行宽闸 md_text_fills_area 同步改判新契约**(88ch 页内探针实测+居中±40+段落填满+纸底)。渲染器抽 services/markdownRender.ts:highlight.js(core+19 语言+别名)接 markdown-it highlight 回调,html:false 安全语义零变化(未知语言回落转义纯文本) |
| 对比度 | 全对令牌 WCAG AA 脚本过秤(≥4.5):亮 #2b2620/#9a4722/#6b6356 于 #faf8f4;暗 #ddd6cb/#d08c5f/#a39a8b 于 #211f1c;代码 token 两主题各 7 色全过(初版 L-string 4.15/L-comment 3.86 调深至 #566d16/#6d6558) |
| 全档 | vitest **90/90**(+6 markdownRender:HTML 转义/hljs span/别名/未知语言回落/任务清单/linkify)+构建过+phase3 **85/85**(+7 纸感守卫:纸底双主题/15px/限宽/衬线标题/赭石链接/自绘复选框/hljs token);实拍计算值+视觉评审确认(demo 对齐) |
| 体积账 | JS 914→1007KB(+93 原始/gzip 318→348):highlight.js 19 语言一次装载驻留模块缓存(与页签数无关);CSS +2KB |
| 版本 | 0.7.23 三处已核;updates=exp 0.7.23(2026-10-14 00:48,UTF-16 核:0.7.23 FOUND/0.7.22 absent,拒发闸 staged 0.7.22→publishing 0.7.23);owner 路径=Update→重启→开任意 MD 双主题验收;桌面 demo 文件验收后可删 |

#### 0.7.22 页签批量关闭(2026-10-13,owner 需求"右键页签可关闭左/右/其他";全部通过)

| 档 | 结果 |
|---|---|
| 需求 | owner 原话三条:关闭该页签左侧所有/右侧所有/该页签之外所有(在既有 Close Tab 之外) |
| 实现 | tabsStore 新增 `closeSiblingTabs(scope: left/right/others)`:锚点=右键的页签必存活;**置顶页签豁免**(Pin=留住的契约,槽位回收已遵循,批量关闭同守约;要关先取消置顶);激活页签被关→锚点接管激活(走 activateFile 全路径:关 Git 视图+树跟随);逐个释放 contentCache(内存纪律)。菜单三项(Close Others/Close to the Left/Close to the Right)+无对象侧禁用态(菜单自己说"没得关",不搞静默空点) |
| 全档 | vitest 84/84+构建过+phase3 **78/78**(+8 批量关闭守卫:左清/右清/其他清×置顶存活+锚点接管+激活保持+禁用态;label 用 Close to the …避开 Close Tab 子串,既有断言零改动) |
| 版本 | 0.7.22 三处已核;updates=exp 0.7.22(17:08,UTF-16 核:0.7.22 FOUND/0.7.21 absent,拒发闸 staged 0.7.21→publishing 0.7.22);owner 路径=Update→重启→开一堆页签右键中间项试三项 |

#### 0.7.21 HTML 双报修复轮(2026-10-12,owner 报障"HTML 不换行/Open in Browser 弹错";全部通过)

| 档 | 结果 |
|---|---|
| 报障 | ①打开 HTML 无软换行,横向滚动条拉特别长(截图);②右键 Open in Browser 弹 Windows 错误框「找不到文件 file:///C:/…」,而资源管理器双击同文件正常开浏览器(截图) |
| 取证 | ②零打扰证据链定案:`open_in_browser` 把 html 拼成 `file:///` URL 交 `tauri_plugin_opener::open_url` → open crate 5.4.4 Windows 后端(非 ShellExecuteW)=PowerShell 脚本(实测 `Test-Path -LiteralPath 'file:///…'`=**False**)→ Start-Process 失败 → 回落 `explorer.exe file:///…` = 截图里那个错框;本机 `.html` UserChoice=QQBrowser.File,真路径 Test-Path=True→Invoke-Item=双击语义(owner 已亲验双击可开) |
| 修复 | ①CodeViewer 加 `EditorView.lineWrapping`(短行不受影响,仅超宽行折行);②handoff.rs html/htm 分支改 `open_path(路径)`(=OS 默认处理器=双击语义),`.url` 分支不动(§115 http/https 白名单原样);死码 `file_url_of`+两测试删除;模块头"opener=ShellExecuteW"失真描述更正 |
| 全档 | cargo 110(112−2 删除)/check 0/0+vitest 84/84+构建过+phase3 **70/70**(含 p10 opener 授权双拒守卫原样通过——修复在 Rust 语义命令侧,不碰渲染层授权) |
| 定向 | 换行:一次性 CDP 探针(临时目录,零打扰,AIV_HIDDEN+park_offscreen)=373 字符单行在 1018px 视口 scrollWidth==clientWidth+行块高 72.8px≈5.6 行(真折行)PASS;浏览器:证据链闭合(见取证),不真弹窗守零打扰红线 |
| 版本 | 0.7.21 三处已核;updates=exp 0.7.21(11:01,UTF-16 核:0.7.21 FOUND/0.7.20 absent,拒发闸 staged 0.7.20→publishing 0.7.21);owner 路径=Update→重启→开 HTML 验收 |

#### 0.7.20 更新重启丢旗标修复轮(2026-10-12,owner『升级完还是不行,但副本没黑线』;全部通过)

| 档 | 结果 |
|---|---|
| 取证 | 零接触三件套定案:正式进程 22:37 启动(已换 0.7.19 磁盘件)但 **psutil environ 实读=旗标没影**(副本=旗标在)——更新器 relaunch(Command::new(exe).spawn() 继承父进程 env)把旧进程设的旧参数串原样带给新进程,lib.rs『变量未设才写』闸门跳过 ⇒ **每次更新重启后新增旗标静默丢失**;全新启动(双击快捷方式)环境干净不受影响——副本与正式版行为分裂的全部原因 |
| 修复 | lib.rs env 补丁改**幂等**(L48):端口按旗名查重(e2e 自设端口不重复追加)+缺旗标即补——任何孵化路径都顶不掉 |
| 全档 | cargo 112+check 0/0+构建过;phase3 环境性阻塞(owner 试验副本开着占开发标识域顶掉测试实例,非代码问题;前端与 0.7.19 全绿轮字节相同)——副本删除后补跑 |
| 版本 | 0.7.20 三处已核;updates=exp 0.7.20(UTF-16+旗标双核);owner 路径=Update→重启(本次重启即实走幂等分支)→快速连点终验 |
| 终验 | **owner 三步完成,黑线灭(2026-10-12 夜)**;正式进程 environ 实读=旗标在位(更新重启路径实走幂等分支,取证闭环);副本已删→补跑 phase3 PASS+r3 8/8。**黑线案七轮全线收口** |

#### 0.7.19 黑线案收口:呈现层修复正式发(2026-10-12,owner 副本验证通过;全部通过)

| 档 | 结果 |
|---|---|
| 验证 | **owner 在试验副本(单变量=--disable-direct-composition)上快速连点:黑线灭**——DComp 呈现层根因坐实;正式渠道发 0.7.19(UTF-16+旗标双核,无 0.7.18 残留) |
| 性能账 | 被动采样运行中副本(带旗标,含真实项目):私有 216.5MB/空闲 CPU 0.08 CPU·s/min——与无旗标 T3 基线 200.2MB/0.12 同量级,无内存/空闲代价;干净 A/B 留给下轮 T3 |
| 全档 | cargo 112+check 0/0+phase3 PASS(Rust 改 lib.rs;e2e 自设浏览器参数,不受旗标影响) |
| 遗留 | owner 确认正式版后可删 Desktop\AIV-黑线试验版(副本开着会占开发标识域,顶掉 e2e 启动——删后恢复);下轮 T3 复测带旗标四档 |

#### 0.7.18 页签拖拽黑线修复轮(2026-10-12,owner 报障"拖动页签冒黑线,连拖必现,瞬态消失";全部通过——**含一次发布事故与重发**)

| 档 | 结果 |
|---|---|
| 根因 | 黑线=**横向滚动条滑块**(overlay 平时隐藏;拖拽把 ghost 拖出条外→Chromium 越缘自动滚→滚动条浮现 ~1.5s 淡出)——owner 副屏窗口(1280)项目条真溢出,主屏黑线为**视口级**滚动条(拖出窗缘时 html 可横滚)。探针复现:帧 3 黑线 y=35 纯黑 74px=thumb(位置=滚动比例),帧 6 视口黑线 x=317,ghost 在条外 |
| 修复 | 三处 `scrollbar-width: none`:html(视口永不横滚)+项目条+文件条(滚动功能保留:滚轮/触摸板/scrollIntoView 照用,VS Code 同做法) |
| 复验 | 探针同场景复跑 6 帧:黑像素计数 0→0;check 0/0+phase3 PASS+recent 21/21+r3 8/8 |
| **发布事故** | **首轮"0.7.18"发布漏 bump 版本号**(tauri.conf 仍 0.7.17)→上架了贴错标签的修复构建;owner 点更新一次成功一次报错("Update failed",疑 AV/transient 锁,重试即过),此后按钮灰"Up to date"而运行进程无修复(磁盘=修复版/进程=旧版)——live-inspect 直连定案(scrollbarWidth=auto+版本 0.7.17) |
| 事故修复 | 真 bump 0.7.18 重发(UTF-16 核 0.7.18 FOUND/0.7.17 absent);**publish-experience.ps1 加同版本拒发闸**(staged update.json 版本==conf 版本→abort,本轮实测"staged 0.7.17→publishing 0.7.18"通过);教训 **L46** |
| 版本 | 0.7.18 三处已核;updates=exp 0.7.18(21:41,UTF-16 核);owner 侧待 Update+重启生效 |

**黑线案五轮(拖拽线已修;点击线两改口,终判=呈现层,试验版待 owner 验)**:①拖拽线=滚动条(帧拍到,0.7.18 修);②点击线'截图拍不到/肉眼可见/秒消'→曾判**面板伪影**——被 owner 拖窗自检推翻(线跟窗走);③owner 给出真触发器=**快速连点**(慢点不现);④快速连点 bursts+同窗口期 72 帧强制合成截图,**owner 眼见线在、全帧零命中**⇒铁证:线在应用像素之上、面板之下=WebView2 **DirectComposition 呈现层**伪影;⑤试验修=lib.rs 默认浏览器参数加 `--disable-direct-composition`(单变量;e2e 自设参数不受影响),**未发正式渠道**——按 owner 指令做成独立副本 `Desktop\AIV-黑线试验版\`(dev 标识/独立存储/可与正式版并行,指纹三验:旗标在/无 .exp 标识/0.7.19),cargo 112+check 0/0+phase3 PASS;等 owner 在副本上快速连点验证:黑线灭→0.7.19 正式发;仍在→查系统层(驱动/MPO)。教训 L47(两次改口留痕)。

#### 0.7.17 项目页签拖拽换位轮(2026-10-12,spec-015;全部通过)

| 档 | 结果 |
|---|---|
| 变更 | 项目页签可拖拽换位:交互模型 **1:1 复用文件页签 L10 方案**(dragenter+dragover 双取消/光标半区 before/after/末尾空带=扔最右,+ 按钮一带也属空带 D3);拖拽≠切换(D4);持久化=数组序零新字段(D2,appState 按序序列化+既有防抖车);store 加 reorderProjects/moveProjectToEnd(splice 模型照抄 reorderTabs 含重找锚点) |
| recent-suite | **21/21**(+6:两项目开/指示线类断言/拖拽翻转/拖拽不切换/空带末尾/状态文件序==UI 序)——**一次全过**,复用打磨模型零返修 |
| 指示线 | 拖拽中截图亲验(p01 底边蓝线+高亮=drop-after) |
| 其余档 | check 0/0+phase3 PASS+r3 8/8(git/pdf 未触及免跑;cargo/watcher 零改动免跑) |
| 版本 | 0.7.17 三处已核;updates=exp 0.7.17(UTF-16 核,无 0.7.16 残留) |

#### 0.7.16 页签 × 二次返修轮(2026-10-12,owner 截图二报"啥回来了?你这是怎么验证的?";全部通过)

| 档 | 结果 |
|---|---|
| 取证 | **live-inspect 直连 owner 运行中客户端**(9322 只读):版本=0.7.15 ✓、close opacity=1 ✓(0.7.15 修复确已生效)——但 **× svg 实际渲染 4×12px**;几何探针(新)证实所有页签(含未截断的)都 4px |
| 根因 | 两层叠加:①`<button>` UA 默认左右 6px 内边距吃掉 16px 盒→内容区 4px,SVG 弹性元素静默缩成 4×12(文字 × 会溢出可见,SVG 不会——雷从 0.7.14 换图标才炸);②长文件名页签(160px 截断)再叠加 flex 挤压。0.7.15 只修了透明度,没碰到这两层 |
| 修复 | `.close` 补 `padding: 0`+`flex-shrink: 0`(名称列 min-width:0 吃全部截断) |
| 验证升级 | visual-check 新增**几何断言**:开长名文件(需求文档 V1.5.md),逐个量 `.close svg` 盒宽 ≥11px——两轮在坏构建上当场拦下(CRUSHED),好构建放行;**截图/视觉模型/像素桶三连在 4px 细条上全翻过车**(视觉模型顺着提问点头/像素桶把细条当图标),几何断言才是终审 |
| 全档 | check 0/0+visual-check 7 张+几何断言过+phase3 PASS+r3 8/8(git/recent/pdf 未触及免跑) |
| 版本 | 0.7.16 三处已核;updates=exp 0.7.16(UTF-16 核,无 0.7.15 残留) |

#### 0.7.15 页签关闭钮返修轮(2026-10-12,spec-014 InTest 期间 owner 截图报障"×都看不到了";全部通过)

| 档 | 结果 |
|---|---|
| 根因 | 0.7.14 给文件页签关闭钮加了"悬停才显形"(opacity:0+hover/active 提亮)——不在 owner 拍板的方案里,自作主张的 VS Code 式收笔;活动页签可见、未活动页签不可见,用户可感即修 |
| 修复 | 关闭钮恢复**常显**:平时 muted 灰、悬停提亮(静音≠隐形);transition 保留 |
| 全档 | check 0/0+phase3 VERDICT PASS+r3 8/8+visual-check 重拍 4 页签 × 全显(git/recent/pdf 未触及免跑);cargo/watcher 零改动免跑 |
| 版本 | 0.7.15 三处已核;updates=exp 0.7.15(UTF-16 核,无 0.7.14 残留) |

#### 0.7.14 视觉改版轮(2026-10-12,spec-014;全部通过)

| 档 | 结果 |
|---|---|
| 变更 | 布局零变化纯换皮:tokens 三档字阶(11/12/13,砍 10/10.5/11.5/12.5/14/15/16 全档)+语义色(--danger 唯一错误红,4 红并存清零;--accent-soft 染色层;--accent-strong 实底专用)+暗色三面阶梯(壳 #16181c/阅读面 #202329/浮层 #262a31+阴影)+Icon.svelte 内联 SVG 16 枚(全 Unicode/emoji 清零)+项目首字徽标 hash 色+文件类型图标族(viewerType 路由同源)+两级标签正交(项目条 40px accent 底条/文件条 28px 细顶线)+100ms 过渡+reduced-motion |
| 对比度 | WCAG 全数值实测(SPEC §六):muted/danger 全底 ≥4.5 两主题;两处返修=亮面徽标字母 72% 混墨(曾低至 2.73)/Up-to-date chip 分主题(暗 0.8=4.68,亮不透明) |
| e2e 同步 | git-suite 徽章 "[7]"→"7"(6 处)+指示器改读 data-state;recent-suite 活动页签改读 .tab-name(L44:断言绑语义元素不绑字形——本轮 1 败即此,修后 15/15) |
| 全档 | check 0/0+vitest **84**(+20:avatarColor 5+iconFamily 15)+phase3 70+git 33+recent 15+r3 8+pdf 23;cargo/watcher 零改动免跑 |
| 视觉自检 | visual-check-014.py 7 张双主题(两级正交/图标/染色层/三面阶梯/浮层全落地);徽标染色层像素抽样证实(视觉模型误读为实底) |
| 版本 | 0.7.14 三处已核;updates=exp 0.7.14(UTF-16 核) |

#### 0.7.13 置顶标记返修轮(2026-10-12,owner 截图报"置顶后子级与名称同列,层级不可辨";全部通过)

| 档 | 结果 |
|---|---|
| 变更 | 树置顶标记从名称前★改为**行尾图钉 📌**(owner 提的改法):前导星占的正是子级缩进列,置顶项名称与子级撞列;行尾图钉让名称回到真实深度列,层级立辨;margin-left:auto 与 git 字母标共存(有字母时紧随其后,均在行尾) |
| 可视化自检 | 截图亲验:Pin to Top 后 src 行尾图钉、名称在顶层列、子级缩进清晰、无星标残留 |
| 全档 | check 0/0+vitest 64+phase3 70/70+r3 8/8+pdf 23/23(cargo/watcher 零改动免跑) |
| 版本 | 0.7.13 三处已核;updates=exp 0.7.13(UTF-16 核,无 0.7.12 残留) |

#### 0.7.12 冻结大案修复轮(2026-10-12,owner 三次现场+「直连活体」指令;全部通过)

| 档 | 结果 |
|---|---|
| 现场#3 | **MISMATCH 行实锤**:store-active 跟手最后点击/页签条 DOM 跟手/viewer-rel 钉死 14:52:40 的渲染——派生对 tabsState 断订阅、对 rootPath prop 活;「扩散」=断的是订阅本身,切到哪个项目哪个死;断链窗口=开机 20s 内(三连快切+10s+切嵌套项目) |
| 本地复现 | v3 配方(4 项目,开机激活≠首位,三连快切+10s+切嵌套+连点)第 0 轮命中一次(页签条+viewer 同死=记录级签名);后续 51+30+15 轮全活(≈2%,统计 A/B 不可行) |
| 修复 | ①App 工作区按 project.rootPath **keyed**(切项目=干净卸载+全新挂载,订阅永不跨重定向变陈旧;内层 viewer 本就按文件+contentRev 重键、§160.5 恢复滚动,增量成本仅页签条重挂)②projectTabs() 创建路径**改回读代理**(裸引用写入对反应性不可见,历来靠赋值 flush 掩护) |
| 活体直连 | ③dev/体验版启动时若未设端口则补 `--remote-debugging-port=9322`(e2e 自带端口优先;**生产打包必须关——已记 spec-011 NSIS 步**)④`window.__aiv.snapshot()` 只读探针(项目/页签/DOM 三对照/日志环)⑤live-inspect.py 只读连接;实测附身运行中实例全量吐出 ✓ |
| 全档 | check 0/0+vitest 64+cargo **112/112**+phase3 70/70+git 33/33+recent 15/15+r3 8/8+pdf 23/23+freeze-probe 6/6(修复版) |
| 版本 | 0.7.12 三处已核;updates=exp 0.7.12(UTF-16 核,无 0.7.11 残留) |

#### 0.7.11 冻结大案取证升级轮(2026-10-12,owner 现场二次报障+首次带诊断取证;全部通过)

| 档 | 结果 |
|---|---|
| 现场铁证 | 诊断 aiv-diagnostics-1791785427:14:09:50–53 **三次快速项目切换**(1.2s 间隔)后,14:09:53.089 起四次页签操作(2 开 2 激活)**零 viewer 事件**——store 与页签条活性正常(live-check:store active=dom-active ✓),唯独 ActiveViewer 的派生死在 05-handoff-wrap.md;**环内零报错**(window error+unhandledrejection 双钩全程干净 ⇒ 非异常路径,是信号图级静默失联) |
| 本地复现 | **两版 42 轮全负**:v1=12 轮(3 项目快速切换+2s 内开/激活);v2=30 轮(+嵌套项目根+git 仓+切换期间盘上搅动);每步断言内容身份——按纪律复现不出不动行为代码 |
| 守卫盲区 | 全部既有断言只查「激活页签名+查看器类名」;冻结恰是页签激活✓+markdown-viewer 类名✓+内容旧——**内容身份从未被任何套件断言过** |
| 取证升级 | ①ActiveViewer `data-rel` 标记(display:contents 包装,零布局风险)②诊断导出加 viewer-rel+**MISMATCH 行**(store active vs viewer showing)③main.ts 捕获 console.error/warn(去重 40 条,setTimeout 延迟入环防 flush 内变更)④盲路径补记:cycleTab `(cycle)`/closeFile 邻位 `(neighbor)`/重开项目 `(re-open)`/新加 `(add)`——现场日志曾因此出现"无因 viewer 事件" |
| 守卫 | phase3 +2:`viewer_rel_matches_active`/`viewer_identity_follows_switch`(**70**/70) |
| 全档 | check 0/0+vitest 64/64+r3 8/8+pdf 23/23;cargo/freeze-guard 免跑(Rust/watcher 链零改动) |
| 版本 | 0.7.11 三处已核;updates=exp 0.7.11(UTF-16 核,无 0.7.10 残留) |

#### 0.7.10 T3 全量基准轮(2026-10-12,spec-011 InTest 收口门;owner 批准"开跑";全部通过)

新建 `scripts/e2e/benchmark-suite.py`(A–I+Baseline 合一;psutil 全进程树**私有字节**口径 §161;结果 %TEMP%\aiv-bench\results.json)。受测=dev release 0.7.10。数字均为实测单轮(启动类 3 次)。

| 档 | 关键数(门全过) |
|---|---|
| A/Baseline | 窗口创建 43ms;**前端就绪 1150/917/1003ms**(CDP 口径,≤2s 门过;可见窗口径零打扰不可复刻,L42);空闲 RAM **私有 200.2MB**(Rust 6.2+WebView2 194.0;WS 429.6)vs §163 target 150 ⚠ 非 gate;空闲 CPU **0.12 CPU·s/60s**(屏外可见口径;隐藏口径 0.3);WebView2 进程 6 |
| B 常规 | 10 页签(5md+3py+2json)+24.9MB;文件切换 p50 34ms/max 42ms |
| C 多项目 | 4 项目×10 页签预置:会话恢复 685ms/重启恢复 718ms/项目切换 p50 33ms(4/4);RAM 223.1(CDP 底座内,看增量) |
| D 大库 | node_modules **105,000 文件**(52s 造,硬链接);启动=常规模(**无递归扫描**);树首显 31ms;监听空闲 CPU 0.03 CPU·s/30s;目录内 300 写风暴 CPU≈0.03+零无响应(忽略过滤实证) |
| E Agent | 60s 278 次写 10 文件:零无响应(WM_NULL 采样);git.exe **79 个**(400ms 防抖合并 3.5:1,理论顶 150;100ms 轮询=下限);徽标终值 10 正确 |
| F PDF | 增量(私有 MB,CDP 底座在增量里消掉):text10 开+101/深滚+233;text100 开+87/深滚+194(**虚拟化:100 页≈10 页**);scan100 开+171/深滚+291 |
| G 多 PDF | 1 页签 +86 vs 5 页签(1 激活)+139 = **1.6×**(线性 5×=+430) |
| H 大 diff | 25k 行工作区 diff → 截断分支 **182ms**("Diff is too large to display."+"Open in VS Code" 在场未点);不渲染全量表(2MB/20k 行后端截断实证);小 diff 176ms 正常;全程零无响应 |
| I 子目录 scope | git-suite 复跑 exit 0(**33/33**,§174 七查在其 BigRepo apps/viewer 实例) |

**PDF 反复开关驻留探针**(5 轮+CDP 强制 GC,补 Phase 5 单轮判断):渲染进程 42→71→81→84MB **平台化**=无 JS 侧泄漏;GPU 进程 94→292→184MB **非单调**=Chromium 光栅缓存自管;Rust/网络/存储全程平 ⇒ **无应用侧无界泄漏**;F 档"close 不立即回落"判读=GC 迟还+GPU 缓存,有界。§163"≤ VS Code 50%"参考项未测(不动 owner 的编辑器实例)。测试基建发现 **L42**(window_of 停错窗,e2e 实际全隐藏口径)。

### 4.1 Phase 1 应用壳(2026-10-01,全部通过)

| # | 验收项(§192 清单 1–7) | 方法与结果 |
|---|---|---|
| 1 | 成功编译 | `pnpm check` 0/0;cargo test 8/8;debug+release 通过 ✅ |
| 2 | 实际启动 | 两构建均启动,标题 AI Project Viewer,Responding=True ✅ |
| 3 | Single Instance | 二次启动 exit 0,进程数保持 1 ✅ |
| 4 | Project Tabs | CDP+UIA:加 Alpha/Beta,active 切换正确 ✅ |
| 5 | Add/Remove/Dedup | picker 全链;右键→确认→tab 消失且**磁盘目录完好**;小写重加→切换已有+toast ✅ |
| 6 | Files/Git/Settings 壳 | 面板切换、Theme 三态、Diagnostics ✅ |
| 7 | 快捷键基础拦截 | 物理注入 Ctrl+R:加速键已禁用(COM)、事件到 DOM、拦截 toast、**页面未 reload** ✅;其余 P0 组合留 owner 手测 |

Rust `resolve_root` 单测:尾斜杠/大小写归一、basename、盘根/文件/不存在/空串拒绝、`\\?\` 剥离。
验收反馈返工:①Remove 入口补到 Files 面板项目路径右键(共享 ProjectContextMenu);②全局禁 WebView 默认右键菜单。

### 4.2 Phase 2 文件树(2026-10-01,spec-002;全部通过)

夹具当时用 `aiv-test-projects\TreeAlpha`(未存档;规格:node_modules/.git/dist、GB18030、NULL 二进制、5/21MB、空目录)。
逐项:Lazy Load 逐层 ✅;系统目录默认隐藏/提示/两清单独立(Rust 8 名单+watcher 11 名单物理分离)✅;Folders First 开关 ✅;Pinned 区手工序混排+同父约束 ✅;拖拽排序(真实鼠标)✅;Rename 保位/Delete 清 Pin ✅;**排序红线(V5):全程磁盘 md5 快照对比,仅测试自身改名/删除动过,其余逐字节未动 ✅**;inspect cargo 24 项 ✅;store 形状 vitest 9/9 ✅。
验收三轮返工:①排序合一(删双模式,§33 增量修订);②Pin 拖拽修复(Tauri Windows `dragDropEnabled:true` 劫持 HTML5 拖拽→置 false,L10;CDP 合成 DragEvent 假阳性,**真实鼠标**验证);③⋯ 并入 Settings;④"拖不到最顶"=落点语义补全+dragenter 也要 preventDefault(L10 补记)。

### 4.3 Phase 3 查看器(2026-10-01,spec-003;全部通过)

夹具=桌面 AIV-TestProject。逐项:Markdown 10 行(渲染/表格/任务清单/代码块/本地图片/内链开 Tab/Source/Raw script 不执行)✅;Text/Code 9 行 ✅;JSON/YAML/TOML ✅;图片 7 行(含 SVG onload/script 双验证不执行)✅;File Inspection(GB18030/UTF-16 解码、binary/huge 守卫、5–20MB 确认框)✅;Tabs 生命周期/Ctrl+Tab ✅;删除态 §83 ✅;§147 Ctrl+R 不 reload/Ctrl+W ✅;cargo 38/38 ✅。
十项验收反馈返工:①内容不刷新=`{#key 文件}`+`$state(Map)`;②图片看不了=二进制判定先于媒体路由(扩展名优先,L12);③固定页签模型(默认累积/右键 Pin 后顶替未固定槽);④页签右键菜单;⑤页签拖拽重排+末位空白带落点;⑥视觉(纯白阅读面/字体栈/字号可调);⑦GIF 实测;外联格式走 opener。回归 16/16。

### 4.4 Phase 4 会话与设置(2026-10-01,spec-004;全部通过)

state.json(version=1)+800ms 防抖+tmp→flush→原子替换+退出双兜底;测试态闸门(§2.1)。
cargo 48/48(原子写/损坏自愈/迁移路由/闸门);vitest 18/18(白名单/往返/字段级自愈);CDP 持久化回归 24/24(当时脚本 aiv-p4-state-test 未存档,断言清单:防抖非即时写/落盘结构/重启恢复全项/损坏自愈+隔离备份/测试态不碰真实 state——**现行重跑以 phase3-suite+pdf-suite 的恢复断言为准,完整持久化套件待需要时按此清单重建**)。
开发中发现:SvelteMap 坑(`$state(new Map())` 零响应性,L13)。
追加:侧栏拖拽调宽(200–600,role=slider+键盘步进,当时脚本未存档,规格见 spec-004 D6)。

### 4.5 Phase 5 PDF(2026-10-01,spec-005;全部通过)

路线:pdfjs-dist 6.3 **legacy build**(modern 对原生 Map 调 `getOrInsertComputed`,L14);worker 走 Vite `?worker`;字节走 read_binary_file(100MB 顶)。
cargo 49/49;vitest 19/19;svelte-check 0/0;**CDP PDF 回归 19/19(现行=scripts/e2e/pdf-suite.py,debug+release 双跑过)**;防退化 P3/P4/侧栏全过。
Benchmark(§98,release+CDP 口径;单位 MB,进程树 RSS;脚本未存档,psutil 按命令行过滤可重建):

| 场景 | before | open | 深滚 | 切离 | close |
|---|---|---|---|---|---|
| A 10 页文本 | 406.2 | 540.6 | 543.3 | 553.9 | 555.2 |
| B 100 页文本 | 401.1 | 533.4 | 565.8 | 576.0 | 551.3 |
| C 100 页扫描 | 395.9 | 684.4 | 831.7 | 705.3 | 709.0 |
| D 5 Tab 仅 1 激活 | 388.2 | 727.7 | — | 699.6 | 692.6 |

判读:①before≈400 是 CDP 调试底座(无 CDP 基线 179MB),**看差值**;②开一个文本 PDF ≈ +134MB,100 页≈10 页(虚拟化生效);③扫描件 +288/深滚 +436(大位图真实代价);④5 Tab 仅 +340≪5×134(非激活只有字节缓存);⑤close 不立即回落=GC 归还延迟,无泄漏性增长。

### 4.6 INFRA-001 体验版与更新机制(2026-10-02;回归 8/8)

交付流程:publish-experience.ps1(自动构建+md5 判定+rename 替换+.old 清理)→ owner 点 Update。测试态 TaskDialog 自动 Later(test_mode_active,L7 补记)。回归当时脚本 aiv-infra1-test 未存档(断言清单:高亮+note/一键更新+回灰/重启后新版/无更新置灰/**开发版与体验版并存互不退出**——现行由 acceptance-r3 部分覆盖,完整套件待重建)。
验收二轮:opener 双层门(capability+scope 白名单默认空全拒,L16)——验证升级到"真程序弹出"层;I-beam 光标;页签 160px 封顶。
验收轮返工:①"点 PDF 没显示"=旧实例占用(单实例激活旧窗);②引擎卸载策略改(owner 拍板"关最后 pdf 页签引擎也卸载")——连带修复 destroy 连环哑炮(L15);③全局文本不可选=user-select 级联修复;④树右键 opener=L12 同族漏网(按菜单族扫)。

### 4.7 划词六轮战史(2026-10-02~10-09;细节全文在 pdf-guide §5 与 lessons L17–L21)

| 轮 | 症状 | 根因 | 验证方式演进 |
|---|---|---|---|
| 1 | 划一行选半页 | textLayer 官方 CSS 变量链没抄全 | 合成验证过但真机坏→暴露"合成≠真实"(L17) |
| 2 | 依旧坏 | **WebView2 143 内核缺陷**(官方对照页:Chrome 154 完美/143 蔓延) | 建"真实输入层+官方对照层"(验证体系 v2) |
| 3 | 升级 155 后"仍有残余" | **测试脚本坐标 DPI 虚拟化错 1.25 倍+前台被聊天窗口抢走** | 坐标自校准公式+前台守卫(L18) |
| 4 | 左上角色块/空白整页选 | br::selection 漏抄/容器可选;顺带 scoped 特异性陷阱 | 零打扰三件套立规 |
| 5 | 最大化右出界蔓选/行首精度 | 无字列无 quad;垫内不能起锚;驱动串台 | 命中垫+手动锚定+rAF 钳制+单例自毁(L19/L20) |
| 6 | 按住+空白上下移动→反选 | 原生把锚点拖到文档边缘,半接管设计被污染 | **锚点按下钉死+全程自驱**(终版,L21);页面内派发测试 |

升级执行记录:143→155.0.4283.45(离线包+管理员;本机 EdgeUpdate 停摆,Edge 停 140)。

### 4.8 关窗行为两轮(2026-10-02/09)

第一版=最小化到任务栏(WM_CLOSE 真路径双验);owner 澄清后改**系统托盘**(✕=隐藏、托盘单击恢复、右键 Exit=唯一真退出;实证 WM_CLOSE→隐藏+存活/二次启动恢复/退出落盘 ✓;托盘菜单为纯 UI 入口留 owner 复验)。

### 4.9 Phase 1 Baseline(V1.5 §162,2026-10-01,release 构建)

| 指标 | 值 | 口径 | 目标 |
|---|---|---|---|
| Startup(窗口可见) | 冷 992ms;温 375/88ms | Start-Process→MainWindowHandle≠0,3 次 | ≤2s ✅ |
| 前端就绪 | 646ms | 诊断面板 startupMs(debug,含 CDP 口) | 参考值 |
| Idle 进程树 RAM | **Private 179MB**(WS 382) | 7 进程(1 Rust+6 WebView2) | ≤150 target(非 gate)⚠️ |
| — Rust / WebView2 | 5.9MB / 173MB(browser79+render45+GPU26+net12+storage9+crashpad2) | | |
| Idle CPU | 0.21 CPU·s/60s ≈0.35% 单核 | 进程树 CPU 时间差 | ✅ |

RAM 判读:超标 19% 全来自 WebView2 空底座(Chromium 最低开销);§163 定性 target 非 gate;压缩手段挂 Phase 10。
机型环境:Win11 + WebView2 143.0.3650.96(划词期已升 155),127.0.98.1 工具链。

---

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-01 | 建,随各 Phase 追加 |
| 2026-10-09 | 验证体系 v2(真实输入层+官方对照层) |
| 2026-10-10 | **整体重写(owner 指令)**:手册区(§0–§3)与历史账本(§4)分离;脚本全量入库 scripts/e2e(电池/套件/夹具生成器/oracle);消除全部 %TEMP% 运行引用 |
