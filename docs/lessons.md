# lessons —— 踩坑全集(只增不删;L 编号被别处引用,不重编不搬家)

> 一条合格的 lesson = **症状(真实报错字眼)+ 一句话根因 + 修法 + 判据**,不是叙事。
> 记的时机:踩坑**当天**,独立 commit。高频坑(被坑 ≥2 次或一次代价大)→
> 同步进 lessons-quickref(那边只放指针)。

## 条目格式

### L1:npmjs 直连不通,`pnpm create`/`pnpm dlx` 不吃 `--registry` 参数

- **症状**:`ERR_PNPM_META_FETCH_FAIL ... registry.npmjs.org: fetch failed`,`--registry` 传入仍打 npmjs。
- **根因**:`pnpm create`(dlx)独立解析 registry,不读命令行 `--registry`;该机器网络到 npmjs 不通(npmmirror 通)。
- **修法**:仓库级 `.npmrc` 写 `registry=https://registry.npmmirror.com`(已入库);一次性场景用环境变量 `npm_config_registry=...`。
- **判据**:凡 pnpm 系命令报 ENOTFOUND/registry.npmjs.org → 先查 `.npmrc`,别反复重试。
- **出处**:Phase 1 脚手架,2026-10-01。

### L2:无 BOM 的 UTF-8 .ps1 含中文 → PowerShell 5.1 按 GBK 误读,报"意外的属性 DllImport"式解析错

- **症状**:脚本含中文字符串(如 `'选择文件夹'`)时,heredoc/字符串解析错乱,报错位置与真实问题无关。
- **根因**:PS5.1 对无 BOM 文件按系统代码页(GBK)解码,多字节字符吞掉换行/引号。
- **修法**:ps1 文件加 UTF-8 BOM(`printf '\xef\xbb\xbf' > f && cat body >> f`),或干脆不含中文。
- **判据**:ps1 报解析错误且位置离谱 → 先查文件里有没有非 ASCII + 是否带 BOM。
- **出处**:Phase 1 UI 自动化脚本,2026-10-01。

### L3:向"当前前台窗口"盲发 SendKeys,按键落进宿主终端(高危)

- **症状**:自动化发 Ctrl+W/Ctrl+F,目标应用无反应,组合键实际发到了前台的应用(本例差点打给宿主 AI 客户端)。
- **根因**:SendKeys 只发给当前焦点窗口;SetForegroundWindow 受 Windows 前台锁限制经常失败。
- **修法**:发键前必须 `GetForegroundWindow() == 目标` 校验,不等于就 SKIP;更稳的路线是 CDP 注入,完全不依赖前台。
- **判据**:任何 SendKeys/SendInput 自动化,先问"键若没到目标会打到谁"。
- **出处**:Phase 1 快捷键验证,2026-10-01。

### L4:WebView2 后台窗口 timer 被 intensive throttling → toast 不消失、PrintWindow 帧冻结,极易误判为渲染 bug

- **症状**:四张间隔数秒的截图 md5 完全相同,toast 常驻不消失。
- **根因**:窗口被遮挡/后台时 Chromium 对页面定时器节流至分钟级,4s 的 toast 超时永远不触发;窗口不重绘,PrintWindow 抓的是 DWM 缓存帧。
- **修法**:验证 UI 动效前先把窗口前台化/恢复;判断"页面 reload 没有"别依赖 toast 消失。
- **判据**:截图帧不变 + 有 pending setTimeout → 先怀疑后台节流,不是渲染。
- **出处**:Phase 1 快捷键验证,2026-10-01。

### L5:Tauri 2 没有 `browserAcceleratorKeys` 窗口配置字段(那是 1.x 的)

- **症状**:`tauri-build` 报 `unknown field 'browserAcceleratorKeys', expected one of 'label', ...`。
- **根因**:Tauri 2 的 WindowConfig 删了该字段,WebView2 的 AreBrowserAcceleratorKeysEnabled 只能编程设置。
- **修法**:Rust 侧 `window.with_webview` + webview2-com `ICoreWebView2Settings3::SetAreBrowserAcceleratorKeysEnabled(false)`(版本对齐 wry 的 webview2-com/windows-core,见 src-tauri/Cargo.toml);已在 src-tauri/src/lib.rs 落地。
- **判据**:V1.5 §147 的加速键冲突需求,查配置找不到字段时走 COM,别找不存在的 conf 键。
- **出处**:Phase 1 编译失败一次,2026-10-01。

### L6:Get-Process 的 MainWindowHandle 可能指向 single-instance 插件的辅助窗口,不是真主窗口

- **症状**:按 MainWindowHandle 拿到的窗口 rect 只有 14×14(最小化虚矩形),截图/点击全打偏。
- **根因**:进程持有多个顶层窗口(`com.aiprojectviewer.app-siw` 辅助窗 + 真主窗),MainWindowHandle 选中哪一个不确定。
- **修法**:EnumWindows 按**标题**精确匹配 'AI Project Viewer' 拿真主窗口;最小化先 ShowWindow(SW_RESTORE) 再量 rect。
- **判据**:窗口 rect 出现 14×14/负值 → 句柄选错了或最小化,先诊断再操作。
- **出处**:Phase 1 UI 自动化,2026-10-01。

### L7:原生 Folder Picker/MessageBox 的自动化:UIA 顶层枚举看不见 owned 对话框、控件 ControlType 全是 Pane

- **症状**:#32770 顶层枚举找不到对话框;找到后按 ControlType.Edit/Button 找不到控件。
- **根因**:对话框是主窗口的 **owned popup**,要用 `GetLastActivePopup(主窗口)` 拿;该对话框 UIA 里所有控件 ControlType 都报 Pane,只有 ClassName(Edit/Button)可靠;后台窗口的 ValuePattern.SetValue 会超时,要用 WM_SETTEXT/BM_CLICK。
- **修法**:组合拳(全部无需前台):GetLastActivePopup → 按 ClassName 定位 → WM_SETTEXT 填路径 → BM_CLICK 确认;确认按钮名带助记符"是(Y)",用 StartsWith 匹配。补充两种弹窗控件形态:文件夹选择器按钮 ClassName='Button';Tauri 消息框(ask)按钮 ClassName='CCPushButton'(不支持 UIA InvokePattern,BM_CLICK 有效);Tauri 消息框要按顶层标题('Remove Project'/'Open Folder')枚举,GetLastActivePopup 可能拿不到。WM_SETTEXT 后必须读回验证——对话框初始化期间会把编辑框重置,曾导致选错目录。脚本:testing.md §1 的 aiv-picker.ps1 / aiv-confirm.ps1。
- **判据**:驱动 Tauri 原生对话框,直接上这一套,别走 UIA 标准模式。
- **出处**:Phase 1 Add/Remove 自动化,2026-10-01。

### L8:WebView2 调试端口参数只在干净启动时生效,残留进程会让端口静默打不开

- **症状**:`WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222"` 启动,进程活着但 9222 不监听,CDP/Playwright 连接 ECONNREFUSED。
- **根因**:上次退出的 msedgewebview2 残留进程占着 WebView2 user data 目录,新进程初始化 WebView2 环境时拿不到干净状态,浏览器参数未生效(无任何报错)。
- **修法**:启动前先清残留:`Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | Where-Object { $_.CommandLine -match 'aiprojectviewer' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`,再带环境变量启动,用 `netstat -ano | findstr 9222` 确认后才跑测试。
- **判据**:CDP 连不上但应用进程在 → 先查残留 msedgewebview2,再怀疑别的。
- **出处**:Phase 1 Playwright 接入验证,2026-10-01。

### L9:建新文档/目录结构前不查指南,自创一套被返工

- **症状**:owner 要求"每段开发写 Spec",agent 没查 AI-Project-Guide 就自创 `docs/specs/phase-N-*.md`;owner 指出应有 spec-NNN 编号、INDEX 台账、workflow 状态机、specs 在仓库根目录——四点全是指南里已有的明文。
- **根因**:指南在手边(Desktop,后入库 docs/AI-Project-Guide/)但只按需读单篇(挂 /wrap 时读过 05);立新结构这种"体系级"动作没先开 00-doc-map.md 总表和 templates/ 对号,凭自己理解发明。
- **修法**:凡要建任何新文档/目录/编号体系,先开【docs/AI-Project-Guide/00-doc-map.md】+【templates/】对号入座;指南有的照抄或明记"为什么不照"(差异写进本项目对应文档,如 docs/workflow.md §五),不许静默自创。
- **判据**:动手建结构前自问"指南里是不是已经有这套?"——没查过就不许建。
- **出处**:specs 体系返工重排,2026-10-01。

### L10:CDP 合成 DragEvent 测不出原生拖拽;Tauri Windows 默认 dragDropEnabled 劫持 HTML5 DnD

- **症状**:树置顶项拖拽换序,CDP `dispatchEvent(new DragEvent(...))` 测试全绿;owner 真鼠标拖拽完全无效。
- **根因**:两层。① 合成事件绕过浏览器原生拖拽发起机制,只走 handler,测不出"拖拽根本起不来";② Tauri 在 Windows 上窗口默认 `dragDropEnabled:true`,OS 级拖放处理拦截 WebView 内部 HTML5 DnD,原生 dragstart 永不触发。
- **修法**:`tauri.conf.json` 窗口加 `"dragDropEnabled": false`(V1 无"从资源管理器拖文件进应用"需求,关闭无副作用);拖拽类交互必须用**真实输入**验证——PS `mouse_event`(LEFTDOWN→分步 MOVE→LEFTUP),窗口用 Chrome_RenderWidgetHostHWND 子窗口定位视口原点,前台锁用"先 keybd_event Alt 再 SetForegroundWindow"绕过。
- **判据**:凡 HTML5 DnD,合成事件测试只能证明 handler 逻辑;发布前必须过一次真鼠标。CDP 连不上/前台锁见 L8/L3。
- **出处**:Phase 2 owner 验收反馈"pin 之间无法拖拽",2026-10-01。脚本:`%TEMP%iv-drag.ps1`。
