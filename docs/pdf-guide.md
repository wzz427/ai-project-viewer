# pdf-guide —— 在本项目处理 PDF(查看/文本选择)的第一读物

> 建立依据:owner 2026-10-10 指令("写一个处理 pdf 文档的经验总结文档,让未来新agent知道如何处理")。
> 血缘:spec-005 全程(2026-10-01~10)沉淀;lessons L13~L21 九条全是它;六轮返工的战史在 §5。
> 谁该读:任何要动 PdfViewer、pdf.js、文本选择,或排查"划词/命中不对"的 agent。

## 0. 一句话总纲

PDF 文本选择 = 在**"绝对定位 + 透明文字 + 无行盒"**的 DOM 上与浏览器原生选择机制共处。
三个层面各自会坏,坏的时候症状互相伪装:**pdf.js 给了什么结构**、**Chromium 怎么做选择**、**你怎么验证**。
**铁律:凡选择/命中类问题,先起官方查看器对照(§4.4)拿到"官方在此环境下是什么行为"的基线,再动代码。**

## 1. 本项目 PDF 架构(2026-10-10 现状)

| 层 | 实现 | 代码 |
|---|---|---|
| 字节通道 | `read_binary_file` → tauri ipc → ArrayBuffer(100MB 顶) | src-tauri,services/tauri.ts |
| 引擎生命周期 | 首开 PDF 才加载 pdfjs;**每文档独立 worker**;关最后 pdf 页签=terminate+丢库(内存最小化,owner 立规) | services/pdfEngine.ts |
| 渲染 | canvas 高清(backing×dpr + CSS 尺寸 + render transform);虚拟化=可视±2 页 | components/Viewers/PdfViewer.svelte |
| 文本层 | pdfjs `TextLayer` API + **官方 css 变量链全量**(§2.3)+ 命中垫(§3.5)+ endOfContent | 同上 |
| 选择驱动 | **自驱**(§3.4):锚点按下钉死,每帧钳到最近行;双击/shift/键盘留原生 | 同上(renderPage 内 mousedown 处理器) |
| 状态 | 页码/缩放/滚动持久化(page≥1,zoom 0.1–5,白名单校验+自愈) | stores/tabsStore |

内存账基准(Phase 5 实测):开一个文本 PDF ≈ +134MB(pdfjs 底座);100 页≈10 页(虚拟化生效);非激活 tab 只有字节缓存;关页签引擎归零。

## 2. pdf.js 集成硬知识

**2.1 必须 legacy build。** `pdfjs-dist/legacy/build/pdf.mjs` + 同目录 worker。modern build 对原生 Map 调 `getOrInsertComputed`(upsert 提案),WebView2 稳定版没有,渲染全炸(L14)。

**2.2 三个"绝不"。** pdfjs 对象(doc/task)**绝不进 `$state`**(Svelte 深代理穿透私有字段必炸);**绝不共享 workerPort**(`loadingTask.destroy()` 无条件杀共享 worker,后续文档永挂无报错,L15——每文档 `GlobalWorkerOptions.workerPort = new WorkerCtor()`);`$effect` 别拿非响应变量当门卫(早退会漏收集依赖)。

**2.3 TextLayer 结构真相(理解一切选择问题的地基):**
- 每个 span = 一段文字片段:**绝对定位、无类名、透明字**(`color:transparent`),位置/字号靠内联样式+CSS 变量链:容器设 `--total-scale-factor`,span 上 `font-size: calc(var(--text-scale-factor) * var(--font-height))` + `transform: rotate() scaleX() scale()`——**链少一环,span 盒子与画布字形脱节,选择矩形落错行**(v11 教训)。
- 行间 `<br>`:pdfjs 自动插、**无定位规则** → 静态流位置全叠在层**左上角**(官方也这样)。必须配 `br::selection { background: transparent }`,否则选中跨行的内容时左上角亮出幽灵色块(v12 教训)。
- 官方完整查看器比裸 TextLayer API 多的东西:`.endOfContent`(层底零高条带,`user-select:none`,`.selecting` 时 `top:0` 铺满=选择期盾片)+ mousedown 切 `selecting` 类 + pointerup/blur 复位。**Chromium≥148 官方自己都跳过位置编排**,class+css 就够。
- **抄官方 css 要全量抄**(对照 `node_modules/pdfjs-dist/web/pdf_viewer.css` 的 `.textLayer` 块),半抄必踩坑;且注意**特异性**:官方靠"等特异性+后写者胜"排层序,搬进 scoped 选择器会翻转(z-index 陷阱,见 §5 第四轮)。

**2.4 官方行为基线。** pdf.js 官方查看器**本来就有**"拖进无字空白→选区跳文档首/尾"的行为(oracle 实测 1182c/12L)——我们后来做得比官方好(Adobe 式钳制),但排查时**别把官方也有的行为当成我们移植错了**。

## 3. Chromium/WebView2 选择机理(血换的)

1. **无字列必蔓选**:文字区域侧面的空白列里没有任何选择 quad,原生拖选延伸进无字列时,焦点直接落到**文档起点/终点**(最大化窗口右出界→"当前行往上全选"的根因)。span 没有行盒是 pdf.js 结构决定的,官方同病。
2. **焦点跟可选祖先链走**:指针落在不可选元素上时,原生找最近可选祖先——容器可选=焦点挂容器=整页包裹;**容器不可选+span 自带 `user-select:text`**,焦点弹回最近文本。页面空白区要 `user-select:none`。
3. **原生更新晚于 pointermove**:JS 在 pointermove 里纠正选区会被随后的原生更新覆盖,**一次性纠正是输家,必须 rAF 帧循环重申,松手后终审一次**。
4. **原生连锚点都会拖走**(终版教训):拖动中"每帧重读 `sel.anchorNode` 当基准"的设计,会被原生在无字列里污染的锚点放大成反选怪态。**正确设计=锚点在 mousedown 瞬间用 `caretRangeFromPoint` 钉死,拖动全程自己写选区,独占写权**;双击/三击(detail≥2)、shift 扩展、键盘选择放行给原生。
5. **不能在 padding 上起锚**:命中垫(padding+负margin,字形与绘制不动——range 矩形只跟文字)解决了"命中范围",但原生不肯在无字区域**开始**选择——垫内按下要手动锚定到最近字符。
6. **驱动必须单例+自毁**:每手势注册的窗口监听/rAF 循环,若没随 pointerup 干净退出,残留循环会**用下一个手势的指针位置续写旧锚点的选区**(串台,数字对账可定位)。修法:组件级 `activeDriver` 单例,新 mousedown 先杀旧,8s 超时自毁,pointercancel 兜底。

## 4. 验证规程(最重要的元教训;**体系正典住 testing.md §1.2,此处为 PDF 场景摘要与专属细节**)

**4.1 合成 ≠ 真实。** CDP 合成鼠标与真实鼠标**不走同一条选择代码路径**(L17);且合成输入在 JS 写过选区后,后续 move 会被浏览器吞。分层下药:
- 纯 DOM 逻辑(我们自己的驱动)→ **页面内派发非可信事件**(new MouseEvent/PointerEvent)完整可测;
- 原生路径 → 真实输入层,或可信 CDP 输入(仅测不写选区的场景)。

**4.2 真实输入层坐标必须自校准。** `比例 = 客户区宽(GetClientRect)/innerWidth`,`屏幕 = ClientToScreen 原点 + CSS×比例`。**别乘 devicePixelRatio**——测试进程与 app 的 DPI 感知上下文不同,虚拟坐标≠物理坐标,×dpr 会错整整 1.25 倍(L18)。

**4.3 前台守卫。** 手势前查 `GetForegroundWindow`;不是目标就**点击**自家窗口未被遮挡的区域(用 WindowFromPoint 探测可见点;拖标题栏会变成拖窗口)。owner 在旁边用电脑时前台随时被抢,特征是"手势突然全死且 selectionchange=0"。

**4.4 官方 oracle。** 15 行驱动页起官方完整查看器(`pdf_viewer.mjs` 的 EventBus/PDFLinkService/PDFViewer + `web/pdf_viewer.css` + legacy build),同一 WebView2 里并排对比——"是我们还是上游/内核"一测便知。搭建样板存 `%TEMP%\aiv-oracle\`。

**4.5 场景保真。** **先问清/复刻 owner 的确切条件**:窗口状态(最大化!)、出界方向(左/右/下)、手势路径(按住上下移动)——本轮三个"修好了又没好"全是场景没对齐。

**4.6 零打扰测试(owner 立规,2026-10-09)。** 三件套:`AIV_HIDDEN=1` 启动 → `SetWindowPos` 移**屏幕外**(-2500,保持渲染;最小化窗口的 caretRangeFromPoint 会读到过期布局)→ CDP/页面内输入。**永远不许抢 owner 的鼠标、弹窗抢前台**。宽屏场景用 `Emulation.setDeviceMetricsOverride`。

**4.7 WebView2 版本先查**(读 `navigator.userAgent`)。**143 有内核级选择缺陷**(对 transform 透明文本层,官方页同样蔓延),**155 已修**。升级:引导器/winget 静默装对 per-machine 安装报 `0x80040828`(无管理员权限直接放弃,连 UAC 都不弹)——**唯一可靠=离线包 `Start-Process -Verb RunAs /silent /install`**;本机 EdgeUpdate 自动更新停摆,别指望它。

## 5. 战史:六轮返工,每轮"症状→当时判断→真实根因→为什么误判"

| 轮 | 症状(owner) | 当时的判断 | 真实根因 | 误判为何发生 |
|---|---|---|---|---|
| 1(v11) | 划一行选中半页 | textLayer CSS 变量链没抄全 | **对**,但只对了一层 | 修完用**合成**验证通过就发了——合成≠真实 |
| 2 | 还是坏,质疑验证 | 一度误诊为 $state 代理 | WebView2 **143 内核缺陷**(Chrome 对照完美) | 验证体系没立起来,被 owner 点破后才建真实输入层+官方对照页 |
| 3 | 选 A 升级后"仍有残余" | 以为还有代码层 bug | **我测试脚本的坐标错 1.25 倍(DPI 虚拟化)+ 前台被聊天窗口抢走** | 自己的仪器不准,读数漂移当成被测物坏了 |
| 4 | 左上角色块;空白区整页选 | 官方机制没抄全 | **对**:br::selection 漏抄;容器可选;顺带踩"scoped 选择器翻转特异性"把盾片抬到 span 上,选择死锚点 | 抄官方 css 半量的旧债;移植时没核对特异性等价 |
| 5 | 最大化右出界蔓选;行首要精准点击 | 命中范围问题 | **对一半**:垫+锚定修了;但驱动残留串台(下一手势指针×旧锚点) | 半接管设计(原生管文字、我管空白)天然不稳定 |
| 6 | 按住划选+空白上下移动→**反选** | — | 原生把锚点拖到文档边缘,被每帧重读的基准放大 | 同上;终版=锚点按下钉死+全程自驱,一轮收口 |

**总账:六轮里真正"代码错"的只有 1.5 轮;其余是内核缺陷(1)、仪器错误(1)、移植欠账(1)、设计半吊子(1.5)。** 费时的根源不是难,是**每轮都在拿不准的仪器上测不准的东西**。

## 6. 未来动 PDF 的检查清单

- [ ] 读本文 + lessons L13–L21;
- [ ] 涉选择/命中:先起官方 oracle 拿基线(§4.4),确认"官方在此环境的行为"再定义"什么算坏";
- [ ] 改 TextLayer/样式:对照官方 `pdf_viewer.css` **全量**,核对特异性;改完跑 v14 全场景电池+右键复制等 r3+PDF 19 项(脚本暂在 `%TEMP%\aiv-v14-test.py` 等,**正式化入库仍挂账等 owner 点头**);
- [ ] 疑内核:先查 UA 版本(§4.7),拿官方页对照,别改代码;
- [ ] 一切验证走零打扰 harness(§4.6,正典=testing.md §1.2);需要 owner 复验的场景,写清"点更新到 0.4.x 后试什么";
- [ ] 发版:0.xx 制(一需求一段,本需求 0.4x;下需求 0.50;全齐 1.0.0),bump 三处版本+`publish-experience.ps1`。

## 7. 已知边界(未做,别误当成 bug)

- 搜索是页导航级(D5),字符级高亮框未做;
- 扫描件无文本层,不可划选(正常);
- 跨页拖选支持(驱动按"全部已渲染页的行"取最近行);
- PDF 100MB 硬顶、页签状态持久化范围见 spec-005。

## 修订记录

| 日期 | 变更 |
|---|---|
| 2026-10-10 | 建立(owner 指令);内容=spec-005 全程六轮返工+lessons L13~L21 的体系化 |
