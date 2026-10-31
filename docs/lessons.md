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
- **补记(2026-10-02)**:消息框(ask)已随插件升级为 **TaskDialog**——按钮是内绘的,**没有子 HWND,BM_CLICK/UIA 全失效**(窗口找得到、子控件枚举为空);自动化场景一律走 `test_mode_active` 分支跳过原生确认(AIV_TEST_PROJECT 家族),真机交互留给 owner 复验。
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

### L17:CDP 合成鼠标 ≠ 真实鼠标的文本选择——交互类验证必须过真实输入层

- **症状**:PDF 划词两轮修复,合成(CDP mouse)回归全绿,owner 真机"点一下选半页"。同代码同页面:Chrome/新版 Chromium 完美,WebView2(140)蔓延——**WebView2 的原生选择实现路径与合成事件路径行为不同**(对 absolute+transform 透明文本层)。
- **根因**:验证层失真。合成事件不触发浏览器原生选择算法的完整路径(且 AIV_HIDDEN 隐藏窗口的 dpr=1,owner 屏 1.25,双重失真)。
- **修法**:验证体系 v2(testing.md §4):合成层只测逻辑;**布局/几何断言过 dpr override(1.25);选择/拖拽/命中类交付前过真实输入层(Win32 SetCursorPos+mouse_event,屏幕坐标=ClientToScreen 原点+CSS×dpr)**;疑上游问题用官方对照页并排。**判据:凡"我验证通过但 owner 说不行"的交互类问题,先怀疑验证层失真,不要先改代码。**
- **出处**:Phase 5 PDF 划词两轮返工,owner 质疑"你现在到底是怎么验证的",2026-10-09。

### L18:真实输入层的两个陷阱——DPI 虚拟化坐标错 1.25 倍 + 前台被抢的"假死"

- **症状**(L17 后续,升级 WebView2 143→155 验证期):①同 app 同手势,一轮测出"蔓选 461/569 字符 5-6 行",下一轮同手势又干净,结果漂移;②一轮里前几个手势正常、后面**全部选 0 字符且 selectionchange=0**。
- **根因(两个独立陷阱)**:①**DPI 虚拟化**:测试进程(python/ctypes)与 app 的 DPI 感知上下文不同,`GetClientRect`/`ClientToScreen` 拿到的是**虚拟化坐标**,"CSS×dpr"公式把它当物理坐标用,落点整体偏 1.25 倍——偏进 PDF 行间隙时 Chromium 按整行粒度选择,看起来像"蔓选 bug";②**前台被抢**:owner 点回聊天窗口后,真实鼠标(mousedown)全打到前台窗口,目标页一个事件都收不到(特征:`selectionchange=0`),像"功能突然全死"。
- **修法**:真实输入层坐标**自校准,不猜 dpr**——`比例=客户区宽(虚拟)/innerWidth(CSS)`,每页现算,`屏幕=客户区原点+CSS×比例`;**每个手势前查 `GetForegroundWindow`**,不是目标窗口就真实点击自家标题栏带回前台(等效用户行为;SetForegroundWindow 仍是禁用的抢前台手段)。**判据:真实输入测试结果漂移/忽好忽坏 → 先查坐标自校准比例与前台归属,再怀疑被测代码。**
- **附带**(同日):WebView2 Evergreen **per-machine 更新必须管理员权限**——引导器/winget 静默装都报 `0x80040828 已为系统安装`(不弹 UAC 直接放弃);离线包 `Start-Process -Verb RunAs /silent /install` 才真更新。本机 EdgeUpdate 自动更新停摆(Edge 停在 140),内核问题先手动升级运行时再说。
- **验证**:修正后官方对照页与 app 同电池 8 手势逐项打平全绿(testing.md §4)。
- **出处**:owner 拍板 A(升级 Runtime)当天的升级+复验,2026-10-09。

### L19:移植官方 css 别信"源顺序",scoped 选择器会翻转特异性;选区焦点跟"user-select 的祖先链"走

- **症状**(升级 155 后 owner 二轮报障):①选行时页面左上角亮出色块;②拖选进入空白=整页蔓选。修①补 `br::selection{background:transparent}`(pdf.js 行间 br 静态流全叠层左上角,官方本来就有这条);修②页面空白 `user-select:none`+span 自带 text+官方 endOfContent 盾片。
- **根因(移植坑)**:官方 css 里"endOfContent 压在 span 之下"靠**等特异性+源顺序**;搬进 Svelte scoped + `:global()` 后 span 规则(`.pdf-text-layer > :not(.markedContent)`)比特异性质反超,盾片 z-index 变 1 盖住一切命中,**选择 0 字符死在锚点**。**判据:移植第三方 css 后交互变死,先查选择器特异性是否等价,再查 z-index 实算值(elementFromPoint+computedStyle 一测便知)。**
- **选区机理(记档)**:拖选中指针落在不可选元素上时,Chromium 找**最近可选祖先**当焦点——容器可选就整页蔓选;容器不可选+span 可选,焦点弹回最近文本(=官方结构)。另:拖选出窗口边界会触发**选区自动滚动**,测试落点必须限窗口内;pdfjs 的 span 无类名,`focus.parentElement.className=='pdf-text-layer'` 很可能是 span 而非容器,**诊断以矩形几何为准别以类名为准**。
- **验证**:行内→边距拖=单行单矩形;8 手势电池/r3 8/8/PDF 19/19 全绿;v12 已发布。
- **出处**:owner 155 后复验二轮报障,2026-10-09。

### L20:无字列的选区延伸跳文档起点;JS 纠正要打帧循环;驱动必须有单例+自毁

- **症状**:最大化窗口划到行尾继续右移出文字区→当前行往上全部蔓选;行首稍左选不中。官方 pdf.js oracle 复现同样行为(非移植错)。
- **根因**:pdf.js span 无行盒,文字侧空白列无选择 quad;Chromium 拖选延伸在无字列把焦点落到文档起点。行首起选失败=垫内无文字节点不肯起锚。
- **修法三层**:20px 命中垫(绘制不动)+mousedown 手动锚定(caretRangeFromPoint)+**rAF 帧循环钳制**。**判据①:原生选择更新晚于 pointermove,一次性 setBaseAndExtent 会被覆盖,必须帧循环重申,松手后终审一次。②凡"每手势注册的窗口监听/循环",必带单例击杀(新手势先杀旧)+超时自毁+pointercancel——本次残留循环用下一手势的指针续写旧锚点选区(146c=旧行锚×新指针位置,数字对账定位)。**
- **零打扰测试**(owner 立规):AIV_HIDDEN+窗口移屏幕外(保持渲染;最小化窗口 caretRangeFromPoint 读到过期布局,屏幕外才准)+CDP 合成输入+Emulation 宽度模拟。**合成盲区**:拖选中合成 pointermove 被吞,垫内起选合成驱动不了——此类路径留给 owner 亲手复验,别硬凑合成断言。
- **出处**:owner 三轮报障+"不要抢我鼠标"立规,2026-10-09。

### L21:选区驱动的锚点必须按下即钉死;"半接管"必然被原生拉扯成怪态

- **症状**(v13 复验):按住划选后鼠标在空白区上下移动,原选区消失、之外的字符全被选上(反选状)。
- **根因**:v13 驱动对原生起手的手势**每帧动态读 `sel.anchorNode` 当基准**——原生在无字列会把锚点本身拖到文档边缘,被污染的基准经钳制循环放大成大范围选区;两写入方(原生+钳制)拉扯的终态不可预期。**判据:凡与浏览器原生行为"共管"同一状态且双方都会写,基准必须一次性钉死、己方全程独占写权;每帧重读共享状态=把对方的污染当输入。**
- **修法(v14 终版)**:mousedown 用 caretRangeFromPoint 钉死锚点(行首垫内按下同样适用);rAF 每帧把终点钳到指针**最近的文本行**(行集合=全部已渲染页,跨页可用);双击/三击/shift/键盘保持原生(detail≥2/shiftKey 放行)。单例+自毁沿用(L20)。
- **测试技法**:页面内派发非可信 mousedown/PointerEvent 可完整驱动纯 DOM 监听逻辑,绕开"可信合成输入在 JS 写选区后 move 被吞"的盲区——**自驱逻辑用非可信事件测,原生路径用可信输入测,分开下药**。
- **出处**:owner v13 复验四轮报障,2026-10-09。

### L22:同路径 exe 静默换图标后,桌面/任务栏不重画——三层验证定位缓存层;发图标资产必附"重启资源管理器"提示

- **症状**(0.5.0 换图标复验):owner 报"桌面图标、任务栏图标没变,托盘里的变了"。快捷方式 IconLocation=`,0`(跟随目标程序)本身没指错,目标 exe 也确已更新(md5 与 updates 一致)。
- **根因**:rename 自替换是静默换文件,①壳图标缓存按"路径+索引"存,不主动重抽;②**即便解析层已是新图,Explorer 桌面/任务栏已绘制的画面也不重画**——实测 SHChangeNotify(ASSOCCHANGED) 广播对这台 Win11 无效,唯一可靠手段=重启 explorer+清 `%LOCALAPPDATA%\Microsoft\Windows\Explorer\iconcache_*.db`。
- **判据/修法(分层验证,哪层坏修哪层)**:V1 `ExtractAssociatedIcon` 抽 exe 内嵌图标比色=证"新图进文件没";V2 `SHGetFileInfo(SHGFI_ICON)` 探针比色=证"解析层新不新";V3 全屏截屏+视觉复核=证"画出来了没"。三层对应修法:换文件/等缓存/重启 explorer。**凡发布含图标资产变更,update note 必写"重启资源管理器"提示(本次已写,owner 有预期)。**
- **判定不做**:updater 换完文件后自动发 SHChangeNotify 刷新——此机实测广播无效,唯一有效手段(重启 explorer)不宜由应用代杀系统进程;换图标事件频率≈项目周期一两次,note 提示已覆盖。重评条件:图标类资产转为频繁发版。
- **出处**:owner 0.5.0 复验报障,2026-10-10。

### L23:几何/挂载类改动回归必须含"resize→跨类型切换";发布版本号一个需求段只发一次;未复现的偶发卡死装观察哨而非硬修

- **症状**(owner 2026-10-10 13:37 报障):另一会话发完 0.5.0(缩进线+PDF ResizeObserver 重构)后,"最大化之后切换窗口,别的文件内容都显示不出来",截图内容区连 Loading 都没有;状态文件停在报障前 2 分钟再没刷盘。
- **排查过程(方法论留档)**:①合成复现×3(Emulation 视口/恢复路径+真实拉宽/最小化恢复)全不现;②中性复读截图纠偏——先前视觉分析被我提示词里的文件名带偏,真实页签=README/ARCHITECTURE/pyproject(先证词后假设的反面教材);③owner 亲手复现+CDP 全程监测:零 console 零 pageerror,跨类型切换全正常 → **未复现,判定为疑似更新重启首会话的偶发**。
- **判据①**:凡动窗口几何/组件挂载生命周期(ResizeObserver/IntersectionObserver/页签切换路径),回归必须含"视口拉宽后跨类型(md↔code↔pdf)来回切换仍渲染"用例——单一查看器内验证(48004 只测了 PDF 自身贴合)看不见跨组件交互。已入 phase3-suite(`resize_then_cross_type_switch`)。
- **判据②**:**发版纪律**——版本号在发布脚本里从 tauri.conf 读,动代码的会话若不自己升版本就会踩别人的段号(48004 提交写 0.4.2、实际发布却打了 0.5.0=图标段的号)。规矩:**每个会话发版前先核三处版本号是不是自己的段**。
- **判据③**:偶发且不可复现的卡死,**先装全局错误哨(window error/unhandledrejection→console.error)留观,不硬修不猜**——修一个复现不了的 bug 等于对着影子开枪;哨已入 main.ts,再犯必留名。
- **出处**:owner 报障"最大化后切换内容空白,验证环节为什么没拦住",2026-10-10。

### L24:验收断言必须直接对着 owner 原话写,不能拿"修法自己的副产品"当判据;UI 统一类改动必须跨查看器比几何

- **症状**(0.6.0 复验打回):①owner"右侧空白还是很明显"——0.6.0 的修法是"860px 列居中",断言写的是"左右对称";对称 ≠ 没有空白,235px×2 的空带照样刺眼。②"操作栏高度不一致"——交付只断言了"工具栏存在",没量过 MD 与代码/JSON 的工具栏是不是同 y 同高(旧 .code-host/.host 的 8px 垫高把它们压低了)。
- **判据①**:把 owner 原话翻译成可判定断言时,断言对象是**他的不满本身**("文本块宽度≥文本区-80"),不是**我选的修法的属性**("居中了")——修法自证等于没验。判据翻译这一步过不了,后面全绿都是假绿灯。
- **判据②**:凡"统一/一致"类 UI 需求,断言必须是**跨组件几何对比**(同 y、同高、同缩进),单一组件的"存在性断言"看不见不一致。
- **修法**:0.6.1——MD 阅读列上限删除(铺满);三处 8px 垫高删除;断言 `md_text_fills_area` + `toolbar_aligned_md_vs_code`(phase3 26/26)。
- **版本规则修订(owner 同轮立规)**:固定 0.6.x 递增不跳段,记入 SPEC-INFRA-003 D7。
- **出处**:owner 二轮复验"为什么验证不到?给我反思",2026-10-10 15:10。

### L25:外部程序"真弹出"验证标准再立功(真机轮抓住探测 bug);单实例应用验证看标题不看新窗口;绝无验证过焦点前发全局按键

- **判据①(真机轮不可省)**:外部移交类功能(开程序/开窗口)的验证标准是**真程序弹出**(Phase 5 已立),不是"命令返回 Ok"。本轮 VS Code 探测路径漏了 `%LOCALAPPDATA%` 下的 **Programs** 段(真路径 `Local\Programs\Microsoft VS Code\Code.exe`),cargo 单测喂的是假目录、全绿;真机轮第一跑立刻抓出"VS Code was not found"。**探测类逻辑的单元测试喂不出现实路径的错——只有真机轮能。**
- **判据②(单实例应用)**:Win11 记事本是单实例标签式——`notepad.exe <file>` 不开新窗口,而是在**已存在的记事本窗口里开一个新标签**(窗口标题变为"文件名 - Notepad")。验证这类移交:断言**已有窗口标题变化**,不是等新 HWND;按新窗口等会误判"没打开"。
- **判据③(全局按键红线)**:想给外部窗口发键(如 Ctrl+W 关标签),必须**先验证 GetForegroundWindow==目标**再发;AttachThreadInput 也可能拿不到前台(Win11 前台锁)。盲发 keybd_event 的按键会落到当时的前台窗口——本轮一次 Ctrl+W 疑似落进 owner 另一个 ZCode 会话(未证实有损,已披露)。**焦点拿不到就放弃全局键盘,改窗口内消息/UIA,或留给 owner 手动。**
- **附带修复**:phase3-suite 的 STATE 路径自正典化起就藏着一个 BEL 字节(`%TEMP%\aiv-p3suite.json` 的 `\a` 被某轮编辑解释成 \x07),状态隔离一直靠"写盘失败"在裸奔;本轮读 state 文件时才暴露。**教训:路径字符串过手(编辑器/复制粘贴)后,od -c 看一眼再信。**
- **出处**:spec-006 真机轮(V9),2026-10-10。

### L26:测试与 owner 客户端的隔离红线——绝不按进程名杀、绝不按窗口标题找

- **症状**(owner 2026-10-10 原话"开发代码时不敢使用这个软件,感觉随时可能自动关闭文件"):体验版客户端与开发构建**同进程名**(ai-project-viewer.exe)、同窗口标题("AI Project Viewer"),e2e 脚本收尾 `Get-Process <名> | Stop-Process -Force` 把 owner 正在用的客户端一起强杀(强杀无优雅退出,还会丢最近防抖窗口内的状态);`FindWindowW(标题)` 也可能抓到他的窗口挪去屏外。
- **判据(全部 e2e 脚本硬规矩,已抽 `scripts/e2e/aivlaunch.py` 单一真源)**:①杀进程只按 PID(taskkill /T /PID),清扫残留只匹配 **ExecutablePath 在本仓库 target 树内**的进程;②找窗口只按 **EnumWindows+GetWindowThreadProcessId==自己 PID**;③测试态 AIV_STATE_FILE 独立文件(已有);④发布只写 updates 目录(已有)。
- **附带发现**:测试期间 owner 客户端被杀过(0.6.2 复验轮前后),当时未察觉——**"零打扰"不光指不抢前台,还包括不动 owner 的进程与窗口**;零打扰的定义扩入 testing.md §1.2。
- **出处**:owner 复验 0.6.2 三件反馈之第三件,2026-10-10。

### L27:发版产物绝不可落进开发/e2e 的二进制路径;测试启动器要识别"错误渠道的二进制"

- **症状**(2026-10-10 晚):owner 报"文件夹新增文件仍显示为空",复现脚本里测试实例 **111ms 秒退(exit 0)**;排查发现 publish-experience 把 experience 构建直接产到 `target\release\ai-project-viewer.exe`——发版后该文件是 **.exp 标识**二进制,与 owner 正在运行的客户端同标识 → single-instance 移交给他的客户端后自退;他的客户端没开时更糟:e2e **静默测错渠道**。
- **判据①**:一个目录只装一个渠道的二进制——publish 改走独立 `src-tauri\target-exp\`(CARGO_TARGET_DIR),`target\release` 永远是 dev 构建。
- **判据②**:测试启动器(aivlaunch)启动前**字节扫标识**,发现 exp 二进制立即拒绝并指路重建——"秒退/起不来"这类症状先怀疑二进制本身不对。
- **判据③**:发布流程改完必须当场反向验证(发版后 target\release 仍为 dev 标识),不能等下次撞上。
- **连带修复**(本次报障的真因):`loadDir` 缓存短路使**折叠再展开永远读旧缓存**,空文件夹整场会话翻不了身(owner"仍然是空的")→ toggleExpand/loadRoot 改强制重读;新顶层目录仍需 Refresh/切项目(实时监听=Phase 9,Phase 7 加切换/聚焦刷新)。phase3 增 `reexpand_relisa_after_disk_add`。
- **出处**:owner 复验 0.6.3 时报"文件夹里增加了文件,仍然是空的",2026-10-10。

### L28:WebView2 隐藏窗口的页面定时器整体冻结——输入事件才唤醒;启动路径不许依赖 setTimeout

- **症状**(Phase 7 首轮 e2e):AIV_HIDDEN 隐藏启动的实例里,启动扫描 effect 正常跑、refreshGit 正常被调,但 400ms 防抖的 setTimeout 永远不触发(badge 一直不出现);手动点 ↻ 后一切正常。`document.visibilityState` 报 "visible"(说谎)。
- **实证**:CDP `page.evaluate("setTimeout(()=>console.log(...),300)")` 在无输入的隐藏页面同样不触发,直到下一次 CDP 点击事件才补发——**隐藏 WebView2 的 timer 队列被渲染器冻结,不是节流是停摆;输入事件是唤醒源**。IPC(invoke 往返)不受影响,只有定时器停。
- **判据**:e2e 里"逻辑没跑"但"交互后全好" → 先怀疑隐藏窗口 timer 冻结,别查业务代码;验证法=evaluate 一个带 console.log 的 setTimeout,再看下次输入后是否补发。
- **修法(产品侧,不只是测试侧)**:启动/新增项目的 git 扫描改 **refreshGitNow 直取**(顺带快 400ms);防抖只留给聚焦/手动/切换——这些路径只在窗口可见(醒着)时发生。既有 800ms 状态保存防抖不受影响(隐藏时本就该攒着,退出有 Rust 兜底落盘)。
- **连带**:git-suite 的 rmtree 需先清 git 对象只读位(git 把 .git/objects 标只读,Windows rmtree 直接 PermissionError)。
- **出处**:spec-007 git-suite 首跑 badge 永不出现,三层探针定位,2026-10-10。

### L29:release GUI 构建必须 `pnpm tauri build --no-bundle`——plain `cargo build --release` 缺 custom-protocol,页面是 ERR_CONNECTION_REFUSED

- **症状**(Phase 8 e2e 首跑):`cargo build --release` 出的 exe 起得来、CDP 连得上,但页面停在 about:blank,内容是 Edge 错误页"localhost 拒绝连接"(devUrl localhost:1420 没人听);25s 等不到 .file-tree。之前轮次一直绿,是因为当时用了正法构建。
- **机理**:Tauri 2 的 `custom-protocol` 特性由 `tauri build`(CLI)注入——启用后走内嵌 frontendDist 资产;plain cargo build 不带该特性,运行时回退 devUrl,而 vite dev server 没在跑 → 连接拒绝。
- **判据**:exe 能起但页面空白/拒绝连接 + URL 落在 localhost:1420 → 先问"这个 exe 是怎么构建的",再看代码。architecture §0/testing §0 已有明文,别凭记忆敲 cargo。
- **出处**:Phase 8 phase3 首跑三连挂,2026-10-10。

### L30:Windows 11 默认控制台宿主是 WindowsTerminal.exe——控制台窗口不在 spawn 者的进程树里;无控制台时 cmd /K 会被 stdin EOF 打死

- **事实一(归因)**:CREATE_NEW_CONSOLE 起的"可见控制台",在 Win11 默认设置下窗口属于 **WindowsTerminal.exe**(独立进程,非 app 子进程)——按"子树内找 ConsoleWindowClass"检测必漏;正确姿势=**系统级可见窗口 before/after 差集**(run-live-check.py 的 top_windows/console_delta)。
- **事实二(无窗测试)**:CREATE_NO_WINDOW 下没有控制台,cmd /K / powershell -NoExit 的交互 stdin 立刻 EOF → 宿主自退,"跑完留窗"性质直接消失(这正是 §118 担忧的机理)。无窗验证宿主存活性要**stdin 塞一根持有不关的管道**(模拟真控制台"输入永不 EOF"),cargo 测试 run.rs 即此法。
- **判据**:测"控制台可见/驻留"类行为,先问宿主模型(Win11=WindowsTerminal),再选归因法;e2e 例行轮永远不真 launch(零打扰红线),真机检走手动脚本+PID 树清理。
- **出处**:Phase 8 真机抽检两轮检测扑空+cargo 宿主测试首败,2026-10-10。


### L31:接管主区的覆盖视图,生命周期必须绑定"打开它的面板/项目"——离开即关,不做驻留

- **症状**(owner 0.6.10 复验,0.6.11 修):Files 开着文件页签 → 切 Git 点条目看 diff → 切回 Files,**页签条消失、主区仍是 diff**。数据没丢(页签 store 完好),是 git 视图还挂着:主区渲染 `{#if gitViewShowing}` 同时藏 FileTabs+渲染 DiffViewer,而切换侧栏模式的 setSidebarMode 只翻模式标志、从不关视图——覆盖视图的寿命没绑定到面板寿命。
- **判据**:任何"接管主区"的覆盖视图(diff/详情/预览),自检两个问题——①除了显式关闭(×/Esc/点文件),还有哪些上下文切换该关它(面板切走/项目切走/窗口失焦?)②有没有一条 e2e 走"开着覆盖视图→切上下文→断言主区归还原主"。覆盖视图挡住的是**别人的地盘**,归还责任在它。
- **修法**:setSidebarMode 离开 git 即 closeGitView;activateProject 切项目即 closeGitView(同族隐患一并堵:项目 A 的 diff 会在项目 B 的 Files 界面继续占着主区)。git-suite 增 git_return_to_files_restores_tabs(owner 原流程复现)。
- **为什么没测出来**:git-suite 的 diff 测试都以显式关闭(×)收尾,从未"不关就切走"——覆盖视图的测试矩阵必须含"不关而切上下文"这条路。
- **出处**:owner 报障原话"再返回到 Files 时,会发现 Files 的文件区那些页签全都丢了,显示的还是 Git 区域的内容",2026-10-10。


### L32:同一处理器里"先改状态再读派生值",读到的是新值——文案/分支先取快照

- **症状**(0.6.9 起存在,0.6.12 修):项目菜单信任切换,状态翻转正确,toast 文案却总是反的("now trusted"显成"no longer")。e2e 断言用了双方都含的子串("trusted for execution"),三轮真机探针都放过了它。
- **机理**:`const trusted = $derived(...)`;处理器里 `setProjectTrusted(root, !trusted)` 执行后,下一行 `trusted ? A : B` 的读取会**同步求值到新值**——先写后读,读到的已是被自己改过的状态。
- **判据**:凡是"翻转语义"的处理器(取反/切换),改前先 `const was = x;` 存快照,文案与逻辑都用快照;review 时看见 `$derived` 出现在 `set` 调用之后的同一函数里就停。测试侧:文案断言必须精确到分支词("is now trusted"),子串断言对"双向文案"是假绿。
- **出处**:owner 真机点 Trust 时 toast 文案与动作相反,时间线探针(t=433 错文案/t=1694 正确 launch)定位,2026-10-10。


### L33:Windows 上 notify 的 rename 是单个 `Name(Both)` 事件带 [from,to] 两路径——不是 From/To 两个事件

- **症状**(Phase 9 首跑):监听链路全通(树自动更新/自动重读/删除态全绿),唯独"改名跟随页签"不跟——页签没拿到 rename 对,树却照常刷新(靠目录重列兜的底,掩盖了根因)。
- **机理**:Windows 后端把一次改名合成**一个** `Modify(Name(RenameMode::Both))` 事件,`paths=[旧, 新]`;按文档里"From 一个事件、To 一个事件"的心智模型写分类器,Both 落进兜底分支当两次普通 Changed,配对永远不发生。写探针打印真实事件形状(`cargo test -- --nocapture` 一次性 probe)一验即破。
- **判据**:跨平台 FS 事件库的事件形状,**按平台实测再写分支**;rename 处理必须有"Both 拆成相邻 From/To"的分支(留 cargo 单测:classify_event_splits_windows_both_rename)。另外配对只认**相邻**(内核的 From/To 紧挨着到),全局 zip 会把同窗内无关的"移出+移入"焊成幻影 rename——这条是被自己的单测打脸后改的。
- **出处**:phase3 watcher_rename_follows_tab 首败+临时探针实证,2026-10-11。

### L34:隐藏 WebView2 冻结的是"定时器队列",不是页面——事件驱动链路里再挂 debounce,等于把 L28 请回来

- **症状**(Phase 9 git-suite):监听触发的 Git 徽标自动涨([8])但不回落([7] 卡死);诊断环显示**两笔 fs-change 都到达、handleBatch 都执行、零报错**——独立探针复刻同一场景却全通。
- **机理**:git-suite 没像 phase3 那样 park_offscreen,AIV_HIDDEN 的从未显示窗口会被 WebView2 挂起;挂起冻的是 setTimeout 队列(L28 原案),而 fs 事件本身是投递任务照常送达。于是 handler 跑了、直接调用(树重列)生效,**handler 里的 400ms 防抖定时器却冻着**——最后一步永远不触发,直到窗口被唤醒。之前手动轮的点击(输入事件)把页面拍醒过,恰好掩盖。
- **判据**:凡是**可能在窗口不可见时到达的事件**(fs 变化/托盘/后台完成),其处理链路禁止依赖 setTimeout;要么直调 Now 型函数,要么把防抖下沉到 Rust 线程(watcher 本体即此法)。e2e 套件一律 park_offscreen(可见但屏幕外),别让"挂起"混进被测变量。gitStore 的 refreshGitNow 注释其实早写了这条,这次是它第一次咬到"新写的代码"。
- **出处**:git_watcher_auto_refresh 稳定失败+诊断环取证+双探针对照,2026-10-11。


### L35:同步命令跑在原生主线程——事件驱动会把"偶尔的重活"变成"常驻占死窗口";渲染进程健康≠窗口没冻

- **症状**(0.7.0,owner 当日打回):软件一打开就卡死——鼠标点任何页签都是 ⌛️ 忙碌光标(原生窗口不泵消息)。e2e 全绿没拦住:phase3/git-suite 的监听检查都在小夹具上跑,每批事件的处理在主线程只占几十毫秒。
- **机理**(三层叠加):①Tauri 2 **同步命令在原生主线程执行**(async 命令才进运行时线程);②`git_snapshot` 是同步命令,每次起 git.exe 子进程(真仓库百毫秒到秒级),Phase 7 以来只被"聚焦/手动刷"偶尔触发,无人察觉;③Phase 9 监听把它变成**每个事件批次都触发**——owner 的真实用法正是"AI 会话持续写文件+观察器开着",批次源源不断,主线程永远在跑 git → 窗口死。复现:33 次写/秒持续锤击,`SendMessageTimeout(WM_NULL)` 测原生窗口线程,40 采样 29 个无响应;修复后 0/83。
- **判据一(测谁)****:⌛️/白影/拖不动 = 原生主线程;页面点了没反应但窗口能拖 = 渲染进程。**CDP evaluate 测的是渲染进程,它健康不代表窗口没冻**——测原生用 SendMessageTimeout WM_NULL + SMTO_ABORTIFHUNG。测负载类回归必须有"持续写入"场景,小夹具单发事件测不出。
- **判据二(写谁)****:会起子进程/走网络的命令一律 `async fn`+`spawn_blocking`(git_snapshot 已改);高频事件链路的前端处理要**单 lane 串行+忙时合并批次**(watcherStore drain),防堆积靠合并不靠丢;**限速别用 setTimeout**(见 L34,隐藏窗会冻)——上游防抖(Rust 400ms)+lane 本身就是限速器。
- **出处**:owner"一打开就直接进入到卡死状态"+⌛️ 截图说明;watcher-freeze-guard.py 复现→修→0/83 验证,2026-10-11。


### L36:notify-debouncer-full 的 FileIdMap 在 watch() 里全树 WalkDir+逐文件开句柄——Windows 默认启用;真实项目(node_modules/构建目录/符号链接农场)=主线程分钟级卡死

- **症状**(0.7.0+0.7.1,owner 两轮打回):软件一打开就 ⌛️ 卡死,CPU 单核 100%。0.7.1 已把 git_snapshot 异步化(L35)仍冻——另一层独立根因。
- **机理**(源码级闭环):①`Debouncer::watch()` 同步调 `add_root`→`cache.add_path`;②Windows 默认 `RecommendedCache=FileIdMap`(只有 Linux 用 NoCache),其 `add_path` 对根做 **`WalkDir::follow_links(true)` 全树遍历+每文件 `get_file_id`(开句柄)**;③owner 的激活项目是真实仓库(node_modules 几十万文件+pnpm 符号链接+两个构建目录),这一走分钟级起步;④我的 `start_project_watch` 是**同步命令=主线程**执行 → 窗口冻死;e2e 夹具 330 个文件毫秒级完成 → 全绿放行。
- **判据**:①凡引入"监听/索引/扫描"类库,先读它 watch/init 的源码路径,问"它在启动时对大树做什么"——**用真实规模目录试一次**(本仓库即最佳夹具);②监听生命周期(启/停/换)永远异步命令+spawn_blocking,主线程只许跑毫秒级活(L35 通则);③依赖库的"默认缓存"常是最贵的路径,确认自己用不用它的功能——我们改名配对用路径 From/To(L33),FileIdMap 纯属白付,`new_debouncer_opt+NoCache` 绕过。
- **取证法**(这次提速的关键):真实状态文件副本+AIV_STATE_FILE+CDP 复现 →"禁用监听"二分构建一锤定音 → 渲染层安静+原生 CPU 满 → 直奔 Rust 侧源码。附:探针用 AIV_STATE_FILE 会被应用回写,复现用状态要每次重新拷贝(旧副本已被测试实例写成空壳,曾造成"健康"假象)。
- **出处**:owner"0.7.0 一打开就卡死/升级按钮都点不了"+0.7.1 换装后仍冻;watcher-freeze-guard 小夹具全绿 → 真实状态 100% 复现 → 禁用监听分叉 → notify-debouncer-full cache.rs 源码,2026-10-11。

### L37:e2e 定位与二进制扫描三坑(0.7.3 recent-suite 首发各付一次调试周期)

- **Playwright `locator(sel, has=...)` 配 `:text-is()` 不解析**(等待到超时也不报错原因):组合 `has=loc('span.name:text-is("x")')` 永不匹配,`has=loc('span.name', has_text="x")` 或外层 `.filter(has_text="x")` 立即命中。写行级定位一律用 `filter(has_text=)`;名字在夹具内须无子串歧义(p00..p11 互不为前缀)。
- **CSS 属性选择器把 Windows 路径反斜杠当转义**:`[data-path="C:\Users\..."]` 的 `\U` 被吃成 unicode 转义 → 永不匹配。按路径定位 DOM 一律改按**文件夹名文本**;确要按属性,得先转义反斜杠——不如换锚点。
- **嵌入标识/资源字节可在 4MB 窗口之外**:对 exe 做标识断言(exp/dev identifier、字符串探测)必须**全文件读**(aivlaunch._assert_dev_binary 本就全读;swap-experience-client.py 首版只扫前 4MB,0.7.3 实测标识落在窗口外会误判"非 exp 构建"拒绝换装,已修)。5.9MB 文件全读无成本,别开窗口。
- **出处**:recent-suite 15/15 跑通前的探针对照(A/B/C 三定位变体一次验明)+发版后三二进制标识核验,2026-10-11。

### L38:CSS 变量驱动的样式 + 缓存布局测量的库(CodeMirror)=累积漂移;修库内部刷新路径不可靠,重建实例才是确定性解

- **症状**(0.7.4,owner 截图"行标号和行字符串没有对齐"):文本/代码查看器里按 A+/A− 调字号后,行号列逐行偏离正文、越往下越歪(14→20px,12 行文件实测偏 100px);滚动一下或内容恰好溢出视口时偶然自愈。默认 13px 时偏移量肉眼不可见——工具栏字号功能(0.6)上线起一直潜伏。
- **机理**:全局字号走 :root 的 CSS 变量(`--viewer-font-size`);CodeMirror 看不见**不是它自己施加**的样式变化——缓存的行高全部过期,而它的行号元素高度是按旧测量值**显式内联**指定的,于是行号列(流式布局)整体按旧行高排、正文按新行高排,两条腿走路。静态打开(挂载时已是目标字号)永远对齐——所以默认字号下从未暴露。
- **弃两条路(探针实证)**:①`requestMeasure()` 是公开 API 但把测量推迟到动画帧——被节流/离屏的窗口(L34 家族)不跑帧;②内部 `measure()`(同步)也不够——行号高度刷新挂在 update 旗标驱动的刷新链上,12 行短文件实测 92px 误差纹丝不动。**别跟库的内部刷新路径搏斗,换确定性结构**。
- **判据**:凡"样式由外部(CSS 变量/主题类)驱动 + 渲染库自带布局测量缓存"的组合,改样式的那一刻必须让库**重建或显式失效**;本项目已有同款确定性模式=watcher 的 contentRev 重挂载(§160.5),照用:字号一变即重建编辑器实例(滚动位置走既有保存/恢复对)。守卫=phase3 `gutter_aligned_across_font_changes`(连按六档后全行偏差<1px+行号字号跟随正文)。
- **出处**:owner 2026-10-11 截图报障;探针四轮(静态两态 0 偏差→复现 −168px→requestMeasure/measure 均不愈→重建后双向全 0),修复随 0.7.4 发。

### L39:cmd.exe 的 /K//C 载荷"见元字符即剥引号重析"——单层引号防不住注入,raw_arg+双层引号才是确定性解(0.7.6 spec-011)

- **机理**(探针实证,Python 字符串命令线复刻 raw_arg):cmd 的 /C//K 文档行为——引号内含 `&<>()@^|` 任一元字符即不保留引号,改走"老规则"剥首尾引号后重新解析。所以 `cmd /K "C:\proj\a&calc&\run.bat"` 实际拆成 `C:\proj\a` & `calc` & `\run.bat` 三段执行(`calc` 从 PATH 真跑出来了);双层引号 `cmd /K ""path""` 剥外留内,`&` 落在内层引号里=字面量,脚本照跑。
- **判据**:①凡 spawn cmd.exe 且载荷含文件路径(路径成分用户可控=项目文件夹名),路径一律 `raw_arg` 双层引号(Rust 标准参数转义走 MSVCRT 规则,与 cmd 的解析规则不同族,别混);powershell.exe 的 `-File` 无此坑(PS 自己解析 argv,`&` 不特殊)。②验证注入类问题必须真 spawn 断言行为(marker 文件写没写),只看 argv 字符串测不出 cmd 的重析;**载荷命令必须选无害命令**——本轮用 `calc` 实证时真弹了计算器窗口(已清理),反例教材。
- **出处**:spec-011 R16 审计发现 `cmd /K` 裸传路径;两轮探针(单层=注入成立/双层=干净)+cargo 真 spawn 回归 `bat_in_ampersand_folder_runs_via_verbatim_quoting`,2026-10-11,修复随 0.7.6 发。

### L40:内容可划选(user-select:text)的容器会罩住控件区——双击控件=按词选中标签,原生蓝色高亮挂在按钮上(0.7.7)

- **症状**(owner 2026-10-11,0.7.6 复验):连点 A+/A− 调字号,"有时"按钮显示蓝色。截图肉眼难辨,像素扫描在工具栏带找到 (47,99,206) 纯蓝块;活体探针一锤定音:可信双击 A+ 后 `window.getSelection().toString()=='+'`、按钮区域 199 蓝像素;三连击选中 `'A+\n'`(343 像素);120ms 间隔连点不触发——"有时"=连点节奏是否落进双击判定窗口。
- **机理**:为"内容可划选"立的 `.viewer-body { user-select:text }` 把工具栏一起罩住;Chromium 对 `<button>` 文字默认**没有** user-select:none,双击按词选标签,选中色=系统蓝。CSS user-select 是**继承属性**:容器级 none 会顺着罩进 `<input>`,把输入框的双击选词/全选拖选弄坏——输入框必须显式恢复 `user-select:text`。
- **判据**:控件区与内容区分治——全局 `button { user-select:none }`(按钮是控件,永远不是复制目标)+ 工具栏容器 none + 容器内 input 显式 text;验证只信活体:双击后 selection 字符串为空(机器可判),别靠截图肉眼(本次截图里 A/A+ 恰好常态,险些误导)。
- **出处**:owner 截图报障;像素扫描定位疑点→CDP 可信双击/三连击探针实证→修复后同探针 selection 全空/蓝像素回落基线,2026-10-11,修复随 0.7.7 发;守卫=phase3 `toolbar_buttons_not_selectable`。

### L41:两条立过的 UI 规矩打架时,"单一真值"要给"用户可感的当下"让路——右键动作后高亮跳回旧文件(0.7.9)

- **症状**(owner 2026-10-12,0.7.8 验收):右键树里 Notes.txt → Show in File Explorer,资源管理器开了,树高亮却落到 PyProject.toml(右键前打开的文件)上。探针复刻原场景实证:无点击穿透(菜单项下方不是树行),PyProject.toml=当前激活页签——高亮是"还给"它的。
- **机理**:两条规矩的乘积——①树高亮单一真值=激活页签(2026-10-10,治"树和页签高亮漂移");②右键高亮=菜单期瞬态独占(0.6.12,治"右键不高显")。①×② ⇒ 菜单一关,高亮必然还给激活页签;而用户刚对 X 做了动作,感知上"高亮跳到了别的文件"。规矩各自正确、组合翻车,且潜伏到 owner 真用"右键→移交"才现形。
- **判据**:①"瞬态/持久"这类交互取舍,必须枚举**关闭路径**逐条问用户感知:点了动作关闭≠点空处关闭——前者是"对 X 的操作完成",X 应保持高亮;后者是"取消",回落才对。②修法=动作关闭不清 contextMenuTarget(acted 标记),下次文件激活(revealInTree 单一咽喉)交还;③守卫载荷**别用会弹系统窗口的动作**(reveal)——零打扰红线,用同语义的无害动作(Copy Path)替代。
- **出处**:owner 2026-10-12 报障;探针五步实证(激活/菜单开/动作后/无动作关/再激活)全部符合预期后收;守卫=phase3 `context_action_keeps_row_highlight`,修复随 0.7.9 发。

### L42:AIV_HIDDEN 下主窗从未 show,window_of 按"可见"找到的是单实例哨兵窗——park_offscreen 一直停错窗,全部 e2e 实际跑在"rAF 冻结"口径(2026-10-12 T3 轮)

- **发现**:基准轮测"窗口可见"启动耗时时枚举实证:AIV_HIDDEN=1 下主窗(title=AI Project Viewer)IsWindowVisible=False——tauri.conf `visible:false` 创建+setup 里 AIV_HIDDEN 分支跳过 show();进程里另有一扇**始终可见**的 `com.aiprojectviewer.app-siw`(单实例哨兵窗)。aivlaunch.window_of 按 IsWindowVisible 过滤 ⇒ 返回的永远是哨兵窗,park_offscreen 的 SetWindowPos+ShowWindow 全打在哨兵窗上,主窗保持全隐藏。
- **机理**:testing.md §2.1"移屏幕外保持渲染"公式的"找到主窗"一步从未真正成立;套件一直绿是因为 L34 修复(refreshGitNow 直取)+各断言不依赖 rAF/paint(canvas 计数不 paint 也真)。被冻结的实际只有 setTimeout/rAF 一类——"隐藏窗定时器冻结(L28)"口径覆盖全部 e2e。
- **判据**:①要"真实渲染/定时器活"的测量(基准空闲 CPU、启动可见口径),必须按 (pid,title) 找主窗(不看可见位)再 SetWindowPos 屏外+SW_SHOWNOACTIVATE(benchmark-suite.py `show_main_offscreen`);②"窗口可见"口径零打扰下不可复刻,启动改记两段:窗口创建(title 枚举)+前端就绪(CDP body 挂载);③aivlaunch 是全套件共享基建,本轮不动它、在基准脚本内补偿;要统一翻案先全套件对照跑。
- **出处**:T3 全量基准 A 档计时探针(2026-10-12);补偿实现=scripts/e2e/benchmark-suite.py。

### L43:复现不了的现场病,先造「下一现场必中」的取证,再造「直连活体」的通道——不要在隔壁搭仿真环境猜(owner 2026-10-12 冻结大案)

- **证据链**:owner 三次现场,第三次取证版当场 MISMATCH 实锤(store/页签条跟手每次点击,唯独 viewer 派生钉死且随项目切换"扩散");本地 96 轮配方复刻仅中 1(≈2%)——**本地命中率与现场差两个数量级时,统计 A/B 是死路,价值全在「下一现场必中」的取证与「直接上门」的通道**。
- **判据**:①断链定位法=三层对照(store 真值 / 页签条 DOM / 内容区 DOM+data-rel),签名分层(记录级=store 写入失联 vs 组件级=仅派生断订阅)指向不同修复层;②「页签条动+查看器类名对+内容旧」是守卫盲区——**内容身份必须显式断言**(data-rel==激活 rel+正文 marker 互斥),名字/类名断言全绿≠内容对;③owner 直言"软件就在本地开着,你为什么不上门看"——对:CDP 常开端口+window.__aiv 只读探针+live-inspect 只读连接,一次建设终身受益;④端口须在进程启动前注入 env,**正在跑的旧实例无法事后开口**——这机制必须装在"下一版"里,不能案发后才想起。
- **出处**:owner 三次现场+指令(2026-10-12);修复=App 工作区按 rootPath keyed(切项目=干净重挂)+projectTabs() 创建路径回读代理,随 0.7.12 发;守卫=phase3 内容身份×2;通道=lib.rs 常开 9322+debugHook.ts+live-inspect.py(实测附身运行中实例,snapshot 全量吐出)。

### L44:e2e 断言绑 data 属性,别绑字形——UI 图标换装(Unicode→SVG)时,断言跟着皮走就全灭(2026-10-12 spec-014)

- **场景**:视觉改版把全部 chrome 字形(📌⚙↻✕×▸⎇›‹⬆●✓)换成 SVG、Git 徽标 "[7]" 改 accent pill。git-suite 七处断言 `badge == "[7]"` / 指示器 `inner_text() == "●"`——字形即断言,皮一动全红。
- **判据**:①断言的**语义值**(脏/净、计数)与**画法**(字形/pill)分层:语义放 `data-state="dirty"` 这类 data 属性,断言读属性;②选择器绑 class/aria/title,不绑可见文本;③改 UI 文案/字形时,允许同步改断言,但改法是"把断言迁去 data 属性",不是把新字形再硬编码一遍;④Playwright 的 opacity:0 元素仍视为可见可点——图标按钮 hover 才显形不影响点击断言。
- **出处**:spec-014 施工;本轮同步改 git-suite(徽章 "7"、指示器 data-state),五套全绿验证。

### L45:固定尺寸的按钮必须 `padding: 0`——UA 默认 6px 垫会把内容区吃成 4px,SVG 挤成细条而文字会溢出;视觉验证的终审是几何断言,不是截图/视觉模型/像素桶(2026-10-12 ×二次返修)

- **症状**:owner 二次报障"×还是看不见";live-inspect 直连几何读取=svg 4×12px(所有页签,含未截断的)。0.7.15 已修 opacity 却没修到——同一症状两层根因。
- **机理**:①`<button>` UA 默认 `padding: 1px 6px`:16px 盒−12px 垫=**4px 内容区**;SVG 是 flex item,`flex-shrink:1` 下**安静缩到 4px**;旧的文字 × 不缩、溢出边界照样可见——**同一个盒子,文字时代无害、SVG 时代成雷**,换图标那天才引爆。②长名页签(160px 截断)叠加 flex 挤压,按钮本身也被压。修=`padding: 0`+`flex-shrink: 0`。
- **判据**:①固定宽高的按钮一律显式 `padding: 0`(本仓 audit:FileTabs .close 是唯一漏网,Diff/Commit 的 .close 当时写对了);②**视觉验证三件套全在 4px 细条上翻车**:视觉模型顺着提问点头("每个页签都有 ×✅")、像素桶扫描把细条的暗像素数当成了图标、我的截图夹具文件名太短没踩到 clamp 路径——**终审=几何断言**(`getBoundingClientRect` 逐个量 svg 盒 ≥11px,坏构建当场拦);③夹具必须覆盖触发边界(长名/多页签/截断),只测常态=只测了一半;④live-inspect 直连是报障第一动作:这次它 30 秒区分了"没更新/更新没生效/修复没修到根"三种假设。
- **出处**:owner 二次报障(2026-10-12 19:31);修复随 0.7.16;守卫=visual-check 几何断言(两轮拦下坏构建)。

### L46:发布三步(版本 bump→publish→UTF-16 核)是闭环,跳一步就出"贴错标签的幽灵构建"——发布脚本必须自断言,人记步骤不算数(2026-10-12 0.7.18 事故)

- **症状**:owner"无法 update"+Update failed toast+按钮卡 Updating…;现场取证=updates/安装盘/target-exp 三个 exe 指纹全同且 update.json 写"[0.7.17|20:37]"——黑线修复以 0.7.17 的标签发了出去(漏 bump);owner 点击一次成功(磁盘换上修复)一次失败(疑 AV/transient 文件锁),此后 md5 相等按钮永远灰,运行进程到不了修复。
- **机理**:发版流程靠人记"先 bump 三处再 publish 再 UTF-16 核"——那轮 bump 和核都跳了,publish 照常打印 PUBLISHED,**没有任何机械环节会红**;"发布成功"的表象和"发错了东西"长得一模一样,直到 owner 的更新按钮行为反常才现形。
- **判据**:①**发布脚本必须自断言版本已变**:staged update.json 里的版本==conf 版本→拒发(已加,首战即拦:"staged 0.7.17→publishing 0.7.18");②**UTF-16 核一步不可省**——它是唯一能把"标签"和"内容"对上号的机械检查;③experi­ence 渠道排障三件套:update.json note(版本+时刻)/三处 exe md5 指纹/updates 与安装盘 mtime(PS Copy-Item 保 mtime→可还原发布-换装时间线);④同内容重发必须带新版本号:md5 判定下"内容相同标签相同"=客户端永远收不到。
- **出处**:owner 21:32 报障"无法 update";live-inspect 直连定案;重发 0.7.18(UTF-16 核过)。

### L47:黑线案终局——"肉眼可见、一切截图拍不到"⇒线在应用像素之上、面板之下=WebView2 DirectComposition 呈现层伪影;结论两次改口(2026-10-12 五轮)

- **证据链(五轮)**:①owner 报"点项目页签必现黑线,几秒自消",**电脑截图拍不到**(他因此改用手机拍);②CDP 慢速点击+录屏零命中;③一改口"面板伪影"——被 owner 拖窗自检**当场推翻**(线跟窗走;面板伪影应留屏幕原位);④owner 找到真触发器:**必须快速连点**(慢点不现——我此前所有复现慢了所以全空);⑤快速连点 bursts+同窗口期 72 帧强制合成截图,**owner 眼见线在、全部帧零命中**——线上屏、不进帧,铁证。终判:应用像素之上(一切像素截取按定义不可见)、面板之下(跟窗走)=**DComp 呈现层**;试验修=lib.rs 浏览器参数 `--disable-direct-composition`——**owner 副本亲验黑线灭,根因终实锤;0.7.19 已正式发(性能账:带旗标实测 216.5MB/空闲 CPU 0.08,与无旗标基线同量级)。
- **机理**:快速连点=整幅工作区大面积高频换装({#key} 重挂+过渡),DComp 表面更新跟不上时在 WebView 内容区顶缘留深色残条,数秒后下次完整呈现覆盖消散;屏幕截图/页面内 captureScreenshot 读的都是合成后的应用帧,呈现层伪影不在其中。案中**两条黑线两个根因**:拖拽线=真滚动条(帧拍到,0.7.18 修);快速点击线=DComp 伪影(永不上帧)。
- **判据**:①报障"线/影子/拖尾"第一动作=**owner 截图对照**:截图有→软件路径;截图无→**再拖窗自检**:跟窗走=呈现层(DComp/DWM/MPO,走浏览器参数/驱动/系统层),留屏上=面板——两判据各管一层,缺一不可(本案只做第一个就错判面板);②"必现"复现不出时,**追问操作节奏**(速度/顺序/间隔)——本案慢点不现快速必现;③CDP screencast 只在画面变化时出帧(6 秒 3 帧),抓瞬态用 captureScreenshot 轮询(每次强制合成);"owner 眼见+截取全空"同刻成立=呈现层实锤;④双窗口嫌疑先排除僵尸进程(窗口枚举 PID→exe 路径)。
- **改口留痕**:一判"滚动条"——仅对拖拽线成立(已修);二判"面板"——被拖窗自检推翻;终判 DComp。出处:owner 五轮报障+两次关键输入(手机拍屏的动机/快速连点触发条件);全程 live-inspect 直连+经 owner 同意在其客户端驱动点击(CDP 输入,不抢焦点)。

### L48:靠环境变量打的默认补丁,会被"自重启的继承"吃掉——更新器 relaunch 孵化新进程带着旧进程的 env,首写即赢的闸门让新增旗标静默丢失;env 补丁必须幂等(缺啥补啥)(2026-10-12 0.7.19 现场翻车)

- **症状**:owner 更新到 0.7.19 并重启,黑线依旧;同一份二进制的桌面副本却无黑线。**零接触取证**:psutil 读两个进程的 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS`——副本=`--remote-debugging-port=9322 --disable-direct-composition`(旗标在),正式版=只有旧端口串(旗标没影)。
- **机理**:更新器的 relaunch(updater.rs:`Command::new(exe).spawn()`)默认**继承当前进程环境**;旧进程(0.7.18)生前已把该变量设成旧值,新进程里 lib.rs 的"变量未设才写入"闸门一看已有值就跳过——**新增旗标在每次更新重启后静默消失**,而全新启动(资源管理器双击)环境干净、旗标正常。副本与正式版行为分裂的全部原因。
- **判据**:①给进程自身设默认 env 的补丁,必须问"**这个进程可能被谁孵化**":自重启/更新器/守护进程的子进程都带着父辈 env——**幂等确保**(逐旗标查缺补漏)替代首写即赢;②版本类"更新了但行为没变"的排障,零接触三件套:进程启动时间(psutil create_time)对发布时刻+磁盘 exe 指纹(UTF-16)+**进程环境实读(psutil environ)**——本例三步两分钟定案,一行代码没翻;③"某机制在 A 启动路径好使、B 启动路径不好使"=先查两条路径的 env 继承差异,再查代码。
- **出处**:owner"升级完还是不行,但副本没黑线"(2026-10-12);修复=lib.rs env 补丁改幂等(端口按旗名查重,e2e 自设端口不会被重复追加),随 0.7.20。

### L49:"Open in Browser"报「Windows 找不到文件」——tauri-plugin-opener 的 Windows 后端不是 ShellExecuteW,是 open crate(PowerShell→explorer 链),不吃 `file:///` URL;打开本地文件一律交**路径**,URL 只留给 http(s)(2026-10-12 HTML 双报)

- **症状**:owner 右键 Open in Browser 弹系统错误框(标题=file:///C:/…,正文「Windows 找不到文件」);同文件资源管理器双击正常开浏览器——**应用路径坏、系统路径好**,第一时间就该对比两条路径差在哪。
- **机理**:`open_url(file:///…)` → tauri-plugin-opener 2.7 → **open crate 5.4.4**(模块头"ShellExecuteW"的旧认知是错的)→ Windows 上先跑内嵌 PowerShell(`Test-Path` 分流:真路径→`Invoke-Item`,否则→`Start-Process`)。`file:///` URL 对 Test-Path 是 **False**(实测)→ Start-Process 找不到 → 回落 `explorer.exe file:///…` → **弹的就是截图那个框**;且 detached spawn 让 invoke 返回 Ok,应用侧无感。修=html/htm 交**解析后的路径**给 `open_path`:Test-Path=True→Invoke-Item=**双击语义**,三平台通吃(`open`/`xdg-open` 本来就吃路径)。
- **判据**:①给"打开"类 API 传参前先问:**这个后端认路径还是认 URL**——Windows Shell 生态认路径,浏览器认 URL,`file:///` 是两者的三不管地带;②"代码看着对但行为错"时,把依赖的**插件→crate 链路翻到叶子**(opener→open 5.4.4 的 windows.rs),注释/文档里的后端描述会过期,源码不会;③零打扰验证链:Test-Path 实测(URL False/路径 True)+`.html` UserChoice 注册表读关联+owner 已验的双击行为,三段拼出全程,不弹一个窗;④e2e 零打扰红线下,"真弹浏览器"的终验交给 owner 的 Update 路径,不在测试里破例。
- **出处**:owner 2026-10-12 报障(截图+「双击能开」关键对照);修复随 0.7.21(handoff.rs html 分支改 open_path,删 file_url_of 死码);同轮顺带修 CodeViewer 无软换行(lineWrapping 一行,probe 实证折行)。

### L50:exe 卡按钮渲染成纯文本——全局 `button` 样式重置下,每个卡片自带按钮样式;**抄样式要抄全,结构断言(元素在)不算视觉验证**(2026-10-26 0.8.15 返修)

- **症状**:owner 截图打脸:"你这哪是按钮啊?怎么验证的?"——exe 信息卡两个按钮渲染成两行裸文本(无边框/无底色);phase3 守卫全绿放了行。
- **机理**:app.css 全局 `button { background:none; border:none }`(桌面美学重置),各卡片在 scoped style 里**自带**按钮补丁样式(padding/边框/底色/hover)。0.8.15 抄 UnsupportedViewer 样式时只抄了 `.actions` 布局与 `button.primary` 字重,**漏了 scoped `button` 本体规则**→按钮落到全局重置=纯文本。守卫只断言 `button.count()==2`(结构),样式层零覆盖。
- **判据**:①改**视觉**的交付,验证必须是"眼看(截图)或计算样式断言"之一,结构在≠样子对(L45 几何断言的同族教训,这次是没做任何视觉验证);②全局样式重置的项目里,给卡片加按钮=布局类+**按钮本体规则**一起抄,对着抄来的文件 grep `button {` 确认;③返修守卫要封死本轮盲区:p8_exe_info_viewer 已加计算样式断言(边框≥0.5px 计算值/背景非透明/内边距≥4px——1px CSS 在 125% DPI 下计算值是 0.8px,阈值别写 1)。
- **出处**:owner 2026-10-26 看 0.8.15 截图质问;返修=0.8.16(scoped button 样式补齐+探针截图亲验+守卫加样式断言,探针断完即删)。

### L51:三图标"没对齐"——**目测与视觉模型指认的方向都不可信,像素级问题先几何量测**(2026-10-31 spec-017 轮)

- **症状**:owner 报"三个图标的高度根本就没有对齐"(侧栏头部新增第三枚图标后)。视觉模型看图判"放大镜偏高、齿轮偏低、刷新居中";实际几何量测(icon-align-probe.py 在页栅格化 svg 算墨迹中心+按钮盒高)推翻:**三个墨迹中心只差 0.12px(不可感),真凶是刷新按钮盒高 26.5px、另两个 23px**——`.glyph` 的 `display:inline-block` 让行内 svg 落在文字基线上,多出 3.5px 降部空隙,按钮被撑高、图标相对顶高 ~1.75px。改 `inline-flex` 一行收口,三钮同高。
- **机理**:inline-block 容器里的 inline svg 按**行内文字**排版(基线+降部),不是按盒子排;图标包一层 span 想做动画锚点时,span 必须 flex 化,否则每个包过的图标都比不包的高一截。
- **判据**:①对齐/偏移几个 px 的问题,**先量测后动手**(CDP 在页把 svg raster 到 canvas 算墨迹 bbox,或 getBoundingClientRect 比盒),别拿目测或模型口供定方向——视觉模型对 2-3px 偏移的方向判读会错(L45"4px 细条全翻车"同族,这次连方向都反);②修完必须回归量测确认(三钮同高),再走视觉模型出图终审;③潜伏缺陷常在被"第三者"打破对称时暴露:两枚图标错位 1.75px 挂了数周没人报,加第三枚立刻显眼——加东西时顺手量一下**左邻右舍**的几何,别只验新加的。
- **出处**:owner 2026-10-31 对话报障(截图);修复随 0.8.18(.glyph inline-flex);phase3 加 header_icons_aligned 几何守卫(按钮高差+svg 中心差 <1px)封回归。
