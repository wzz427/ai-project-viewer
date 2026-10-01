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
- **判据**:凡 HTML5 DnD,合成事件测试只能证明 handler 逻辑;发布前必须过一次真输入。CDP 连不上/前台锁见 L8/L3。
- **出处**:Phase 2 owner 验收反馈"pin 之间无法拖拽",2026-10-01。脚本:`%TEMP%iv-drag.ps1`(已废弃,见补记)。
- **补记(同日二轮)**:① **dragenter 也必须 preventDefault**,否则 WebView2 里 drop 事件根本不触发(dragover 拦了也没用;实测 enter:7→drop:1)——行与面板的接受逻辑要同时挂 dragenter+dragover;② 拖拽落点语义补全:行上/下半=插前/插后,置顶区上方空白(路径框一带)= 插到最顶,否则"甩到顶"落进死区;文件页签同族同修(拖不到最右,2026-10-01 三次反馈)——**凡拖拽排序,永远带 before/after 双语义**,只有 before 的实现必然够不着末位;且**容器空白带必须显式接落点**(页签条末尾空白、路径框一带皆死区,要给语义:条末空白=追加末位)——自动化要复现"人手甩过头的落点",精确落元件中心的测试测不出死区;③ **测试脚本禁止抢 owner 前台**(SetForegroundWindow/Alt 技巧/SW_RESTORE 全部禁止——owner 明确抱怨被打断);拖拽验证改用 **Playwright connect_over_cdp(pywork)**,输入走 CDP 管道零前台,窗口用 SW_SHOWMINNOACTIVE 起最小化不激活。脚本:`%TEMP%iv-p2-drag-test.py`。

### L11:隐藏窗口测 GUI:窗口 show 闪现与可信输入两层坑

- **症状**:owner 两次抱怨测试打扰——①应用启动瞬间窗口弹出再被最小化;②旧法(启动后 SW_SHOWMINNOACTIVE)仍有闪现。
- **根因**:①调试期间反复重启应用,每次正常启动都置前;②最小化是"显示后再收",第一帧仍上桌面;③根治后发现新坑:从未 show 过的 WebView2 窗口收不到 CDP 可信键盘输入(Input 层),Playwright keyboard 全失效。
- **修法**:tauri.conf `visible:false`+应用启动显式 show;测试态 `AIV_HIDDEN=1` 跳过 show(窗口永不出现),`AIV_TEST_PROJECT` 自动加项目(免原生选择框,它也会上桌面);键盘测 dispatcher 用 DOM 合成 keydown(物理链路 Phase 1 已验)。Playwright evaluate 只传**一个**参数对象——按位置收多参全 undefined,曾让全部合成按键静默失效。
- **判据**:GUI 测试标准启动式见 testing.md §1;凡"测过但用户说没反应",先查输入到底走的哪一层。
- **出处**:Phase 3 自测,2026-10-01。

### L12:菜单"点了没反应"两连坑:卸载后读 prop 抛异常;图片被文本二进制判定拦截

- **症状 A**:页签右键菜单的"View Source/Close Tab"点了毫无反应,同菜单"Keep Tab Open"却正常。
- **根因 A**:菜单 act() 先 onclose()(卸载菜单组件)再执行动作闭包;Svelte 5 组件卸载后闭包再读其 prop(如 tab.markdownMode)直接抛异常,**把整个 handler 吞掉**——无报错无效果。Keep Open 恰好不读需要响应性的字段所以幸存。诊断法:在 handler 两端埋 window 标记,一段有一段无=中间抛了。
- **修法 A**:**动作先执行、后 onclose()**;或进 handler 先快照字段值。凡"先关弹层再做事实体"的写法都要过这条自检。**补记(2026-10-02)**:树右键菜单的 "Open with Default App" 是同族漏网——当时只修了页签右键菜单,树菜单的 `onclose()` 先执行再读 `name` prop,handler 被吞、点了毫无反应(owner 报障"不管什么文件都没反应")。判据升级:**L12 修复要按"菜单族"扫一遍,不是修单个菜单**。
- **症状 B**:PNG/JPG/GIF 全部显示"Binary file",SVG 正常。
- **根因 B**:图片字节天然含 NULL,文本检测流水线判为二进制;而开文件流程先查二进制再查图片扩展名,图片永远进不了查看器。
- **修法 B**:路由顺序=超大守卫→图片扩展名(媒体通道)→二进制→文本。判据:**二进制判定只对文本通道有意义**,按扩展名的专用通道要放在它前面。
- **出处**:Phase 3 owner 十项验收反馈,2026-10-01。

### L13:Svelte 5 `$state(new Map())` 没有响应性——深代理只包 plain object/array

- **症状**:会话恢复后页签永久卡 "Loading…"。控制台证明内容已读到、`cache.set` 已执行(钩子函数读同一 Map 返回有值),但 `$derived` 读它恒为旧值 null。更迷惑的是**正常开文件路径一切正常**——因为 openFile 先 set 缓存、后写 activeFileRelativePath,是后一个**对象字段写**顺带触发了 derived 重算,掩盖了 Map 本身不响应。
- **根因**:Svelte 5(5.57 实证)`$state` 深代理在 proxy.js 里只处理 `Object.prototype`/`Array.prototype` 两种原型,**Map/Set 原样返回、零追踪**;`Map.get` 不收集依赖、`Map.set` 不触发失效。
- **修法**:换官方响应式容器 `import { SvelteMap } from "svelte/reactivity"`(API 兼容,零迁移);**判据:凡容器要参与 UI 反应链,一律 SvelteMap/SvelteSet,`$state(new Map())` 等于普通变量**。
- **验证**:tabsStore 换 SvelteMap 后,持久化回归 24/24、Phase 3 回归 17/17 全绿。
- **出处**:Phase 4 会话恢复(spec-004),2026-10-01。

### L14:pdfjs-dist 6 对原生 Map 调 `getOrInsertComputed`——新引擎环境必须用 legacy build

- **症状**:PDF 首页渲染全部抛 `TypeError: this[#t].getOrInsertComputed is not a function`,栈指向 pdfjs 内部 `getOptionalContentConfig`/`#methodPromises`;worker 正常、getDocument 正常,只有 render 炸。
- **根因**:pdfjs 6 的代码对普通 `new Map()` 实例到处调用 `.getOrInsertComputed(...)`——依赖**极新的 upsert 提案 API**(Map.prototype.getOrInsertComputed);WebView2 Runtime 143(Chromium 当前稳定)未实现。Svelte 深代理惹的错(`this[#t]` 私有字段撞 Proxy)是**同症状的第一层误诊**——把 pdfjs 对象移出 $state 后错误依旧,才暴露真根因。
- **修法**:import 一律用 `pdfjs-dist/legacy/build/pdf.mjs` + `legacy/build/pdf.worker.min.mjs?worker`(legacy 自带 polyfill);**判据:WebView/Node 环境跑 pdfjs 6 报 `#t`/`getOrInsertComputed` 类 TypeError → 先换 legacy build,再怀疑别的**。附带两条 Svelte 5 连坐坑(同日):①外部库大对象(pdfjs doc/task)**绝不进 `$state`**——深代理穿透私有字段必炸;②`$effect` 里条件早退会**漏收集依赖**(refit effect 首跑 `if (!doc) return` 把 baseW 挡在依赖外,之后永不触发)——**响应式就绪信号要放进条件本身**(如 `if (!baseW) return`),别拿非响应变量当门卫。
- **验证**:legacy build + 上述修正后 PDF 回归 19/19(渲染/工具栏/虚拟化/释放/恢复/搜索)。
- **出处**:Phase 5 PDF spike(spec-005),2026-10-01。

### L15:pdfjs `loadingTask.destroy()` 无条件杀 worker——共享 workerPort 会连环哑炮

- **症状**:先开 PDF A 再开 PDF B,一切正常;切回/关闭 A 后,B 永久停在 Loading(0 个 canvas、无任何报错);引擎未被我们 terminate(日志证明)。
- **根因**:pdfjs(v6 实证)`PDFDocumentLoadingTask.destroy()` 末尾 **无条件** `this._worker?.destroy()`——包括 `GlobalWorkerOptions.workerPort` 指定的共享 worker;第一个被销毁的文档把共享引擎带走,后续文档的请求发进死线程,Promise 永挂、无异常无超时。
- **修法**:**每个文档一个 worker**(加载文档前 `GlobalWorkerOptions.workerPort = new WorkerCtor()`),destroy 只回收自己的线程,生命周期自洽;另在"最后一个 pdf 页签关闭"时 terminate worker+丢弃库引用(owner 2026-10-02 要求的"关页签=引擎归零")。**判据:凡 pdfjs 多文档场景,别共享 workerPort;destroy 的清理范围要按"它拥有什么"核对,不是按"我希望它做什么"**。
- **验证**:per-document worker 后 PDF 回归 19/19、修复回归 6/6(含关最后页签 worker 线程归零、重开重载)。
- **出处**:Phase 5 owner 验收轮(spec-005),2026-10-02。

### L16:opener 权限≠opener scope——capability 里放行了,插件白名单仍全拒

- **症状**:右键 "Open with Default App" 对一切文件弹 `Cannot open: Not allowed to open path C:\...`(owner 报障 txt/pdf 全一样);之前自动化只断言过"无关联扩展会报错 toast"——把"动作执行了"当成"功能通了",验证盲区。
- **根因**:Tauri 2 plugin-opener 有两层门:capability 权限条目(`opener:allow-open-path`)**和插件自身的 scope 白名单**——后者默认为空,任何路径都 "Not allowed"。两层都过才真开。
- **修法**:capabilities 里用对象形式带 scope:`{"identifier":"opener:allow-open-path","allow":[{"path":"**"}]}`;URL 同理收紧 `https://**`/`http://**`。**判据:凡 Tauri 插件"权限配了还是 Not allowed"→ 查第二层 scope;凡外联功能,验证必须到"真程序真弹出"层**(本次实证:右键 txt → 记事本弹出并打开文件 → 自动关闭)。path:`**` 的安全边界靠调用点自律(只拼树内相对路径),已在调用处注释。
- **出处**:Phase 5 owner 验收二轮,2026-10-02。
