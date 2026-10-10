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
| T3 全量 Benchmark | V1.5 §166–§174 A–I 档 | owner 批准后(V1 收口前) | 数小时 |

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
| `phase3-suite.py` | 查看器+移交+树交互回归 **56 项**:MD/代码/JSON/图片/页签/编码/快捷键/工具栏 + Phase 6 三右键菜单分型/复制 toast/两端同源/VS Code Mode 持久化 + **Phase 8:Run 菜单矩阵(ps1/py/exe/msi)/exe 信息卡/未信任自动取消/项目菜单 Refresh+Trust 翻转/失败 toast+**底部右键钳制守卫(script/exe/project 每按钮在视口内,0.6.10 增)** | 凡动查看器、页签、右键菜单、handoffMenu/run.rs/trust |
| `git-suite.py` | Phase 7 Git 检视 30 项:三实例(BigRepo 根=正常/apps\viewer=子目录 §174/AIV-TestProject=非 Git)——徽标计数/页签 ●✓/树标记字母/面板分组/点击开 diff(wt+staged)/同文件双组单计/超限守卫/手动刷新 + **0.6.8 返修:并排 diff 双侧断言/Git 视图期间隐藏文件页签/name+dir+letter 分段排版/提交时间单位/提交详情钻取→提交视角 diff→返回与关闭**;夹具每次在 %TEMP%\aiv-p7-gitscope 重建 | 凡动 git.rs/GitPanel/gitStore/徽标/树标记/DiffViewer/CommitDetailView/diffSideBySide |
| `acceptance-r3.py` | 验收轮 8 项:更新按钮位置/MD 任务清单/右键 Copy/文本层 | UI 通用改动 |
| `real-input-battery.py` | 真实鼠标 8 手势电池(app+官方 oracle 双模式,前台守卫) | **仅 owner 明确许可占用鼠标时** |
| `run-live-check.py` | **手动专用**(会开真控制台窗):Phase 8 运行真机检——信任菜单翻转→Run Script→WindowsTerminal 控制台出现+脚本体执行+结束后驻留;系统级窗口差集归因(Win11 默认终端宿主不在 app 子树) | 动 run.rs/信任门时手跑一次;**绝不入例行轮** |
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

实现期两教训(lessons L29/L30):release GUI 构建必须 `pnpm tauri build --no-bundle`(plain cargo build 缺 custom-protocol,页面 ERR_CONNECTION_REFUSED);Win11 默认终端=WindowsTerminal.exe,控制台窗不在 spawn 者进程树内,检测须系统级差集。

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
