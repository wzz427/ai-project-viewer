# spec-003 · Basic READ(点一个文件能看到什么:File Tabs + 五类查看器 + 五快捷键)

> 状态:Ready —— 真值 = specs/INDEX.md。
> 创建:2026-10-01;Pre-Draft 结论:owner"可以了,做spec003"(spec-002 Done 同句);免审门适用(workflow §五 A2/A5,写法同 spec-002:R/V 挂 V1.5 节号指针,不抄正文)。
> 需求源:V1.5 §177(Phase 3 批次);完成判据:§188 READ 各块 + §147 Ctrl+R 验收条款 + §192-7。

## 〇、值不值得做

Phase 3 是 V1.5 §175–182 排期定死的第三批,判:做(应用从"看结构"变"读内容",主工作区首次点亮)。

## 一、Pre-Draft 结论

- 核心选择题:无新增须问项;V1.5 已定栈(markdown-it §87、CodeMirror 6 §107)与行为(五快捷键 §146)。
- 标杆对照:File Tabs 对照 VS Code 编辑器标签;Markdown 对照 GitHub Rendered 观感。
- **界面确认基线**:§86(Rendered|Source 切换)、§108(Formatted|Source)、§109(Fit/Actual/Zoom/Pan)已含界面明文=已确认;未含细节走 §四决策表代取默认。

## 二、需求正文(R 编号;一行 = V1.5 一节,使用者视角提要)

| R# | 需求提要 | V1.5 节 |
|---|---|---|
| R1 | 点文件在主区开 Tab;同文件重开=切到已有 Tab;Tab 可关、可切;Tab 标题=文件名 | §21 §46 §158 |
| R2 | 非激活 Tab 的查看器**卸载**(省内存),切换回来按 FileTabState 恢复滚动/模式 | §21 §160.5 |
| R3 | 双击/单击文件进查看器前走检测流水线:二进制不开文本、>20MB 不整体进 WebView、5–20MB 先确认 `[Open Anyway]` | §101 §104 §106 |
| R4 | Markdown 默认 Rendered,右上 Rendered/Source 切换,Source 只读 | §86 |
| R5 | Markdown 能力:GFM 全套(标题/粗斜/列表/任务清单/表格/引用/行内码/代码块高亮/分隔线)+ 本地图片 + 链接 | §87 |
| R6 | Markdown 安全:Raw HTML 禁用,脚本不执行;项目内链在本应用开 Tab,http(s) 走默认浏览器 | §88 §89 |
| R7 | Text(.txt/.log/.csv):可选中、可复制、Ctrl+F、滚动 | §100 |
| R8 | Code(约 26 种扩展名):高亮、行号、Ctrl+F、复制、跳行、只读 | §107 |
| R9 | JSON 默认 Formatted(美化+高亮),可切 Source;YAML/TOML 走 Code Viewer | §108 |
| R10 | Image(PNG/JPG/WebP/GIF/SVG):Fit、Actual Size、Zoom、Pan | §109 |
| R11 | SVG 只走安全图片上下文(`<img>`),绝不用 innerHTML/iframe/object/embed | §110 |
| R12 | 五快捷键应用级生效:Ctrl+W 关当前 Tab、Ctrl+F 当前查看器查找、Ctrl+Tab/Shift+Tab 切换、Ctrl+R 刷新活动项目(**不得变成 WebView reload,正式验收条款**) | §146 §147 |
| R13 | 当前文件被删:Tab 暂留,显示 "This file has been deleted. [Close Tab]",不崩溃不静默关 | §83 |
| R14 | 读文件按检测到的编码解码(UTF-8×2/UTF-16×2/GB18030),状态可示编码 | §101 §105 |

**反例规则**:二进制内容永不作为文本进 WebView(§104);>20MB 不整体发送(§106);不做 Git Diff/URL 查看器(归属后列);Raw HTML/脚本不执行(§88)。

## 三、验证标准(V 编号;组级指向 §188)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 R2 | 多 Tab 增/切/关/去重;切走再切回,滚动位置与 Rendered/Source 模式恢复;非激活查看器已卸载(DOM 无其节点) | 自动(CDP) |
| V2 | R3 R14 | 二进制点开→二进制提示不开文本;21MB 文本→超大提示;5.1MB 文本→先弹确认;GB18030 文件→中文正常显示且标注编码 | 自动(CDP+单测) |
| V3 | R4–R6 | §188「Markdown」块 10 行逐条过(默认 Rendered/切换/只读/表格/任务清单/代码块/本地图片/内链开 Tab/外链浏览器/Raw Script 不执行) | 自动(CDP)+人工(渲染观感) |
| V4 | R7 R8 | §188「Text / Code」块 9 行逐条过(含 PS1/BAT 高亮、Ctrl+F、只读) | 自动(CDP) |
| V5 | R9 | §188「JSON / YAML / TOML」块 4 行 | 自动(CDP) |
| V6 | R10 R11 | §188「Images」块 7 行(五格式+SVG 安全上下文+脚本不执行) | 自动(CDP)+人工(缩放平顺) |
| V7 | R12 | 五快捷键物理/CDP 注入各一次:行为正确;Ctrl+R 刷新树与活动文件且页面**不 reload**(§147 正式验收) | 自动 |
| V8 | R13 | 删当前 Tab 文件→Tab 暂留+删除提示+[Close Tab] 可关 | 自动 |

## 四、技术实现方案

### 边界(不做清单)

| 不做 | 归属 |
|---|---|
| PDF 全部(含 Asset Protocol spike) | Phase 5 |
| Diff / Git 相关查看 | Phase 7 |
| Show in Explorer / System Default / Open in VS Code / Edit Notepad(>20MB 的两个外联动作为此暂以提示文案占位) | Phase 6 |
| Mermaid、JSON Tree、Ctrl+P、Search Sidebar、Encoding 手动覆盖、Pin File Tab | P1(§186) |
| 状态写盘持久化(内存态,身份相对路径) | Phase 4 |
| 文件实时监听与自动 Toast(§82 的手动版随 Ctrl+R 提供:刷新即重读活动文件) | Phase 9 |

### Rust(2 个新 command,复用 Phase 2 流水线)

- **`read_text_file(root, rel)`**:先走 inspect 流水线 → binary/huge 直接拒(Err);normal/large 返回 `{ text, encoding, sizeBytes }`(large 由前端先经确认框再调用);解码按检测编码,UTF-8 BOM 去 BOM,UTF-16 按 BOM 字节序,GB18030 兜底。
- **`read_media_file(root, rel)`**:图片字节→base64(供 `<img>` data URL;>20MB 拒,SVG 同通道=天然安全上下文 D3)。
- 单测:编码五类解码正确、BOM 剥离、binary/huge 拒、越界拒、边界 5MB/20MB。

### 前端

- **`tabsStore.svelte.ts`**(新):每项目 `openFiles: FileTabState[] + activeFileRelativePath`,形状照 §21(viewerType/markdownMode/scrollPosition/cursorLine/encoding),相对路径身份;开=去重激活,关=邻位激活,重开同文件=复用 Tab。
- **FileTabs 组件**(主区顶部):标签条+关闭钮;树中**单击文件即开 Tab**(D1)。
- **查看器族** `components/Viewers/`:MarkdownViewer(markdown-it,GFM+task-lists,html:false 满足 §88;本地图片 Rust 读→data URL,不碰 asset protocol——那是 Phase 5 PDF spike 的事;内链=相对路径开 Tab,外链=默认浏览器 via opener 插件)、CodeViewer(CodeMirror 6 只读,legacy-modes 覆盖 26 扩展名,行号+搜索+跳行)、JsonViewer(美化+高亮,Source 切换复用 CodeViewer)、ImageViewer(wheel zoom、拖拽 pan、Fit/Actual 工具钮;SVG 一律 `<img src=data:...>`)、UnsupportedViewer(binary/too-large/未知扩展的统一提示态,§83 删除态也走这里)。
- **Inactive Viewer Unmount**(§160.5):非激活 Tab 查看器卸载,状态存 FileTabState,切回恢复。
- **快捷键接线**:dispatcher 五组合接真行为(Phase 1 的 toast 占位退役);Ctrl+R = refreshProject + 重读活动文件;Ctrl+F 只在 Text/Code/JSON-Source 生效(D2),Rendered Markdown 无查找(§188 未要求,V1.5 P1 未列——如需再说)。
- **大文件闸**:5–20MB 文本先弹确认(`Large file. Opening this file may affect performance. [Open Anyway]` §106 原文);>20MB/二进制→UnsupportedViewer 提示(两个外部动作 Phase 6 补)。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 树中**单击**文件即开 Tab | 查看器应用"打开"是主行为;V1.5 未定树-打开交互 | VS Code 式单击预览/双击打开 | 预览态是一套额外状态机,V1 无此概念 |
| D2 | Ctrl+F 范围=Text/Code/JSON-Source | §100/§107 只对这些要求 Ctrl+F | Rendered md 也做查找 | §188 未要求;DOM 查找方案未定,P1 再议 |
| D3 | 图片/SVG 一律 base64 data URL 进 `<img>` | CSP 现状(img-src data:)即可;SVG 天然隔离=§110 | asset protocol | Phase 5 PDF spike 统一定,提前碰 CSP 易返工 |
| D4 | >20MB 与二进制走统一 UnsupportedViewer 提示 | §106 的两个外部动作属 Phase 6 命令,先占位 | 现在实现 Explorer/默认程序打开 | 越项到 Phase 6,且菜单体系未建 |
| D5 | §83 删除态检测点=Tab 激活与 Ctrl+R | Watcher 属 Phase 9,先在自然的重读点检测 | 轮询 mtime | 后台轮询违反 §160.15 |
| D6 | markdown-it `html:false` 而非 sanitize | 输出转义即满足 §88"默认禁用",少一个依赖 | DOMPurify | html:false 无原始 HTML 可注,更简单更稳 |
| D7 | md 编码标注/状态栏这轮先在 Tab tooltip 层给出 | §105 状态栏 UI 未定;先把 encoding 放 FileTabState | 完整状态栏 | 属 Shell 布局,Phase 4 Settings/状态栏一起 |
| D8 | GB18030/UTF-16 解码在 Rust 侧完成再过桥 | 编码_rs 已在 Rust;字符串过 IPC 即 UTF-8,前端零编码逻辑 | 前端 TextDecoder 兜底 | 双份解码逻辑必漂 |

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R3 R14 | V2 | cargo 单测(解码/拒绝/边界)+ CDP 开文件 | TreeAlpha 扩充:GB18030 md、UTF-16 txt、binary、5.1MB/21MB 文本、各格式图片含 SVG | ✓ 夹具计划已列 |
| R1 R2 | V1 | CDP:开多 Tab/切换/关闭/恢复/卸载断言 | 同上 | ✓ |
| R4–R6 | V3 | CDP:渲染断言+Raw `<script>` 注入不执行(§188 硬行) | 带 script/表格/任务清单/内链外链的 md | ✓ |
| R7–R9 | V4 V5 | CDP:高亮节点存在、Ctrl+F 面板、只读 | 各语言样例文件 | ✓ |
| R10 R11 | V6 | CDP:`<img>` 上下文断言+SVG 含 onload 脚本不触发 | evil.svg(内嵌脚本) | ✓ |
| R12 | V7 | CDP 注入+关键物理键(Ctrl+R 必须物理,§147) | — | ✓ 沿用 Phase 1 物理注入法 |
| R13 | V8 | CDP:删文件→断言删除态→Close Tab | — | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | Draft→Ready | R/V 指针化、D1–D8、覆盖矩阵;开工切分:①Rust 读命令+单测 ②tabsStore+FileTabs+树开文件 ③CodeViewer+Ctrl+F ④MarkdownViewer ⑤JsonViewer ⑥ImageViewer+SVG 安全 ⑦快捷键+删除态+大文件闸 ⑧自测+文档 |
| 2026-10-01 | 页签拖拽末位死区二修 | 空白带(最后页签右侧)不接落点,owner 真手势被吞——页签条空白区=追加到末尾(dragenter+dragover 双拦);owner 手势复现→修复实测;回归 17/17 |
| 2026-10-01 | 页签拖拽补 after 语义 | 拖不到最右(只插前同族 bug,lessons L10);页签改左右半分插前/插后,回归 17/17 |
| 2026-10-01 | 页签模型二次澄清返工 | VS Code 全预览模型被否,改为:默认正常累积+固定后顶替未固定槽(回归 17/17);|
| 2026-10-01 | 验收反馈十项返工(InTest 内) | 内容不刷新根因=缓存非响应式+同型查看器不重挂载({#key}+响应式 Map 修);图片看不了根因=二进制判定先于图片路由(顺序修正);预览页签模型+Keep Open(§186 提前);页签右键菜单(模式切换/Keep Open/默认程序打开)+拖拽重排+激活滚入+高亮强化;视觉(白底/字体栈/字号设置);菜单动作先执行后关闭(L12:卸载后读 prop 抛异常吞 handler)。回归 16/16 PASS(零前台);V1.5 §197 审计 4 行;release 重建 |
| 2026-10-01 | Ready→InDev→InTest | ⑧块全落地(3fae581/067809a+收尾);cargo 38/38、svelte-check 0/0、vitest 10/10;夹具=桌面 AIV-TestProject(owner 指定);零前台模式全套自测 30/31 自动+utf16 三重人工(证据 docs/testing.md §2c);release 已重建 |
