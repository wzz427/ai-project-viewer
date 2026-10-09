# spec-005 · PDF.js Spike(点一个 PDF 能看到什么:验证 → 首页 → 完整查看器 → Benchmark)

> 状态:InTest —— 真值 = specs/INDEX.md。
> 创建:2026-10-01;Pre-Draft 结论:owner"可以了,继续spec005"(Phase 4 全闭环同句);免审门适用(workflow §五 A2/A5)。
> 需求源:V1.5 §179(Phase 5 批次)+ §91–§99;完成判据:§188「PDF」块 19 行 + §192-7。

## 〇、值不值得做

Phase 5 是 V1.5 §175–182 排期定死的第五批,判:做(PDF 是 READ 的最后一块大能力;§91 已正式采用 PDF.js、否决 WebView2 Native,无可再议)。

## 一、Pre-Draft 结论

- 核心选择题:无新增须问项;§97 把顺序定死(先验证再 UI)、§92 把功能定死(十项)、§95/§96 把资源策略定死(虚拟化+切离释放)、§98 把数字口径定死。
- 标杆对照:PDF 工具栏对照浏览器内置 PDF 阅读器(页码/跳页/缩放/搜索四件套);虚拟化对照 VS Code PDF 扩展的按需渲染。
- **界面确认基线**:§92 的工具栏功能清单=已确认;具体排布(按钮位置/样式)未含明文,走决策表代取默认(A3),交付可视化验证。

## 二、需求正文(R 编号;一行 = V1.5 一节,使用者视角提要)

| R# | 需求提要 | V1.5 节 |
|---|---|---|
| R1 | 技术验证先行:Local PDF 可加载、PDF.js Worker 真跑在 worker 里、CSP(worker-src/img-src)不放宽安全底线、Worker 生命周期可控、Markdown 本地图片通道复核 | §97 |
| R2 | 点 PDF 文件 → 主区渲染出第一页;PDF 属大文件能力,结构化按页加载,不整页当文本读 | §97 §94 |
| R3 | 完整查看器:上一页/下一页、当前页/总页数、跳页、放大/缩小、Fit Width、Fit Page、Ctrl+滚轮缩放、文本搜索、滚动 | §92 |
| R4 | 切离 PDF 页签保存 Page/Zoom/Scroll,切回恢复 | §93 |
| R5 | 懒加载:未打开 PDF 不初始化查看器模块;首次打开才加载 | §94 |
| R6 | 虚拟化:只渲染可见页±少量相邻页,禁止一次渲染整本(200 页场景) | §95 |
| R7 | 切离后释放 Canvas/RenderTask/Page Cache/Document/Worker 资源,只留轻量状态 | §96 |
| R8 | Benchmark:10 页文本/100 页文本/100 页扫描/5 Tab 仅 1 激活,各记开前/开后/深滚/切离/关闭 RAM | §98 |

**反例规则**:不再比较 WebView2 Native PDF(§91 已决);TOC/缩略图/注释不做(§99 Future);不因 PDF 放宽安全 CSP 到危险程度(worker-src/img-src 最小够用);渲染不得冻结 UI(§188 大原则)。

## 三、验证标准(V 编号;组级指向 §188)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | spike 三项实测记录进决策表:①加载路线(asset protocol vs 字节过桥)带输入输出证据;②Worker 真 Worker(Thread 非主线程,页面无卡顿断言);③CSP 改动最小集+拦截验证(外域 worker 仍被拒) | 自动+人工(spike 记录) |
| V2 | R2 | 点 PDF → 首页可见;同 PDF 重开=切已有 Tab;删除态/超大守卫沿用 | 自动(CDP) |
| V3 | R3 | §188「PDF」块工具栏行:Previous/Next/Page Jump/Current-Total/Zoom/Fit Width/Fit Page/Ctrl+Wheel | 自动(CDP)+人工(观感) |
| V4 | R3 | Search:命中跳转/高亮,无结果有反馈 | 自动(CDP) |
| V5 | R4 R5 | 切走切回 Page/Zoom/Scroll 还原;首开前 DOM 无 pdfjs 模块痕迹(懒加载) | 自动(CDP) |
| V6 | R6 R7 | 100 页 PDF 滚动到深页:渲染页数=可见±缓冲(断言 DOM canvas 数);切离后 RAM 回落、重开可用不崩 | 自动(CDP+进程) |
| V7 | R8 | §98 四场景×五点位 RAM 表落 testing.md;5 Tab 仅 1 激活不线性吃 RAM(§188 行) | 自动(脚本) |
| V8 | — | §188「PDF」块 19 行逐条对(含 Local PDF Asset Protocol/assetScope/CSP 三行,按 V1 落地路线对应理解) | 自动+人工 |

## 四、技术实现方案

### 边界(不做清单)

| 不做 | 归属 |
|---|---|
| TOC / Thumbnail Sidebar / Annotation | §99 Future(V1 后) |
| Diff / URL Viewer | §21 字段预留,后续 Phase |
| PDF 打印/导出/表单交互 | V1 不做(未列需求) |
| Markdown 图片切 asset 协议 | 随 R1 验证;**默认不切**(data URL 已验收),验证结论只记决策表 |

### 前置 spike(块①,§97 优先级的字面执行)

1. 装 `pdfjs-dist`(npmmirror)。
2. **Worker 路线实测**:Vite `?worker` 打包 pdf.worker(同源,CSP `worker-src 'self'` 即可)vs asset protocol 服务 worker 文件——预期 Vite 路线胜(零配置、不碰 scope);实测 worker 线程归属。
3. **数据路线实测**:`getDocument({data})`(Rust 读字节过桥,同图片通道族)vs asset protocol URL(pdfjs 自取)。范围请求不可用则 asset 路线也要全量读,两者内存同量级,选过桥(少一个协议面);若 asset 明显省(懒取字节)再翻。**带数字说话**。
4. **CSP 最小集**:现 CSP 加 `worker-src 'self' blob:;` 其余不动;`img-src` 维持 `self data:`(canvas 渲染不需要 img)。验证:改坏 CSP 一项能拦住(自证有效)。
5. 结论回写本表 D1–D3,块②起按结论实施。

### 前端

- **路由**:`viewerType.ts` 扩展名 `pdf` → `"pdf"`;openFile 路由顺序=超大守卫→图片→**PDF→媒体通道(字节过桥)**→二进制→文本(lessons L12 家族:专用通道在二进制判定前;PDF 天然二进制,不走文本守卫)。
- **PdfViewer.svelte**(`components/Viewers/`):工具栏(页码输入/总数、Prev/Next、Zoom±、Fit Width、Fit Page、搜索框)+ 连续滚动页容器(canvas per page);懒加载=动态 `import()` 首次打开才拉模块(§94);虚拟化=IntersectionObserver 只挂可见±2 页,离屏 canvas 释放(§95);切离(unmount)销毁 document/task/worker 引用,只留 §93 状态(§96)。
- **状态**:`FileTabState.pdfState {page, zoom, scrollPosition}`(§21 已有形状)进 RuntimeTab;持久化白名单带上(Phase 4 管道现成,scrollPosition 同型)。

### 决策依据(后续翻案只翻这节;D1–D3 块①实测后回填 ✅)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | ✅ Worker 走 Vite `?worker` 打包(**legacy build**),CSP `worker-src 'self' blob:` | 同源零配置;回归断言无 fake-worker 回退=真 worker 线程 | asset protocol 服务 worker | 多一个协议面+scope 配置,无收益。**实测修正:必须用 legacy build——pdfjs 6 对原生 Map 调 `getOrInsertComputed`(upsert 提案),WebView2 143 没有,modern build 渲染全炸(lessons L14)** |
| D2 | ✅ PDF 字节走 Rust 命令过桥(`read_binary_file`→tauri ipc Response→ArrayBuffer),`getDocument({data})` | 18.4MB 扫描 PDF 实测通过;零 assetScope 扩大 | asset protocol URL 直读 | 两条路都要全量读(无 Range),过桥少一层协议面;Benchmark 记录内存代价(块⑤) |
| D3 | ✅ CSP 只加 `worker-src 'self' blob:`,img-src 不动 | canvas 渲染无需 img;legacy worker 是同源 chunk | 大幅放宽 connect/img | 安全底线(§143–147) |
| D4 | PDF 不套 >20MB 文本守卫;**字节通道设 100MB 硬顶**(Rust 侧拒) | §95 设计本意扛大文件;但字节全量驻留内存,100MB 覆盖 §98 全部场景,防呆 | PDF 也弹确认 | 结构化渲染无"整体当文本读"问题;顶值代取默认可调 |
| D5 | 搜索=页导航级(逐页文本抽取+命中计数+上一/下一跳页),**字符级高亮框不做** | §92 只要求 Text Search;字符级需完整 textLayer+几何对齐 | 引官方 findController/textLayer | 依赖其 viewer 整壳,难剥离;高亮精度记为已知限制,owner 要再上 |
| D6 | pdfState 四字段(page/zoom/zoomMode/scrollPosition)随白名单持久化,zoomMode 为 §21 字面延伸 | §93 恢复必须含 fit 模式,否则重启后 fit 状态丢;同 spec-004 D7 家族 | 严格 §21 三字段 | 教条对齐牺牲可感体验 |
| D7 | md 本地图片维持 data URL 不切 asset | spike 未启用 asset protocol(零需求);已验收行为不动 | 切 asset URL | 备将来大图内存优化时翻案 |

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | spike 实测脚本(worker 线程断言/CSP 拦截/两路线内存对比) | 任一真 PDF | ✓ 块①出证据 |
| R2 R3 | V2 V3 | CDP:开 PDF/翻页/跳页/缩放/fit/Ctrl+wheel | 10 页文本 PDF | ✓ |
| R3 | V4 | CDP:搜索命中/跳转/无结果反馈 | 含可搜索文本 PDF | ✓ |
| R4 R5 | V5 | CDP:切离切回三字段还原;懒加载断言 | 同上 | ✓ |
| R6 R7 | V6 | CDP:深滚 canvas 数断言;切离 RAM 回落 | 100 页文本 PDF | ✓ |
| R8 | V7 | RAM 脚本(psutil 进程树,四场景×五点位) | 10 页文本/100 页文本/100 页扫描/5 Tab | ✓ 夹具生成脚本随块⑤ |
| 全 | V8 | §188 PDF 块逐行 | 全夹具 | ✓ |

缺口检查:无新测试通道(CDP/RAM 脚本均有先例);夹具生成(reportlab 或等效)是块⑤小事。

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | Draft→Ready | R/V 指针化、D1–D7(spike 预填)、覆盖矩阵;开工切分:①spike 实测(pdfjs-dist+Worker 路线+数据路线+CSP,回填 D1–D3)②路由+PdfViewer 骨架(首页渲染)③完整工具栏(§92 十项)④虚拟化+切离释放+pdfState 持久化 ⑤Benchmark(§98)+回归+文档+release |
| 2026-10-01 | Ready→InDev→InTest | ⑤块全落地(fd8dc19/5acc62c/08596c0+收尾);**spike 实测翻案:必须用 pdfjs 6 legacy build**(modern 对原生 Map 调 getOrInsertComputed,WebView2 143 无此提案 API,渲染全炸;另修 Svelte 连坐两坑:pdfjs 对象不进 $state/effect 早退漏依赖,lessons L14);D1–D3 已回填。自测:cargo 49/49、vitest 19/19、svelte-check 0/0、CDP PDF 回归 19/19(debug+release 双跑)、防退化全绿(P3 PASS/P4 24/24+7/7);§98 Benchmark 四场景数字落 testing.md §2e(判读:多 Tab 不线性吃 RAM ✓);夹具 AIV-TestProject\pdf\(10 页文本/100 页文本/100 页扫描 18.4MB/tab-1..5);release 已重建(2.24MB) |
| 2026-10-09 | 调查定论(验证体系 v2 重建后) | owner 二次报障+质疑验证→建真实输入层+官方对照层(testing.md §4,lessons L17),证据链闭合:**WebView2 Runtime 文本选择内核缺陷(官方对照页在本机 WebView2 蔓延、Chrome154 完美),v11 代码无罪**;阻塞收口,**等 owner 选 A(升级 Runtime)/B(自实现选择层)** |
| 2026-10-09 | InTest 内验收四轮:PDF 划词蔓延修复 | owner 报"划一行选中半页":textLayer 缺官方 CSS 变量链(--total-scale-factor 未设、span 字号未按 calc(var(--text-scale-factor)*var(--font-height)))导致 span 盒子与画布字形完全不符;按官方 pdf_viewer.css 全量对齐+高清 canvas(dpr)+transform 链。实证:单行拖=54 字符 1 行(修复前半页);r3 回归 8/8(拖选改为从真实 span 盒子出发——按比例的坐标会落在行间隙);PDF 19/19;v11 已发布 |
| 2026-10-02 | InTest 内验收三轮 | 四修:① Update 按钮移顶栏最右(owner 位置要求);② **PDF 文本层上线**(owner 以报障形式确认要画布内选字,翻 D5"字符级高亮不做"原判):pdfjs TextLayer 与画布同 viewport 渲染、透明 span 对齐字形,选择/高亮/复制全通,随虚拟化同生命周期;③ 任务列表 label/checkbox 是表单控件默认箭头光标且 label 按下清选区→label cursor:text+checkbox pointer-events:none;④ 查看器右键 Copy 菜单(有选区才弹;修了菜单 mousedown 冒泡到 window 关闭处理把菜单杀在 click 前的竞态)。回归 8/8+PDF 19/19+P3 PASS;v8 已发布体验渠道 |
| 2026-10-02 | InTest 内验收二轮 | 三修:① 右键 Open with Default App 对一切文件报 Not allowed——**opener 第二层门(scope 白名单)默认空**,capability 权限之外(lessons L16);修 scope(path:** 靠调用点自律,URL 收紧 https/http),**真机实证:右键 txt→记事本弹出并打开文件**;② 查看器 I-beam 光标(cursor:text);③ 长名页签 160px 封顶+省略号(title 悬停全名)。回归:PDF 19/19+P3 PASS;owner 顺问"后续 Phase 是否管右键"——否,此即成品路径(§111 泛化),Phase 6 只加更多外联(Explorer/VS Code/记事本);release 已重建 |
| 2026-10-02 | InTest 内验收轮返工 | owner 三反馈:① "点了没显示"=旧实例在跑(单实例激活旧窗),当前 exe 实测正常;② **引擎卸载改为"关最后一个 PDF 页签即归零"**(owner 拍板,§96 强化):per-document worker+releaseEngineIfIdle;**连带发现并修复 pdfjs destroy 无条件杀共享 worker 的连环哑炮**(先关 A 后 B 永挂,lessons L15);③ **文本全不可选 bug**(body 全局 user-select:none 盖住查看器)→ .viewer-body 恢复 text;④ 树右键 Open with Default App 无反应=L12 同族漏网(树菜单未随页签菜单一起修)→ 快照先行(lessons L12 补记)。回归:修复 6/6+PDF 19/19+P3 PASS+P4 24/24;**PDF 文本层(画布内选字)待 owner 表态是否要**(D5 曾排除,要则上 textLayer);release 已重建 |
| 2026-10-09 | **划词闭环:owner 选 A,Runtime 升 155,实测全绿** | Evergreen 143→155.0.4283.45(离线包+管理员;引导器/winget 静默装因 per-machine 无提权报 0x80040828,lessons L18)。升级后真实输入层判决(testing.md §4):官方对照页与 app 同电池 8 手势**逐项打平全绿**(长拖 1 行/右往左/小拖/双击选词);143 时代的"残余蔓选"与"手势全死"分别系验证脚本 DPI 虚拟化坐标错 1.25 倍、前台被聊天窗口抢走(L18)。**app 无需改码发版,重启即新内核;余 owner 复验(v8/v10/v11 一并)** |
| 2026-10-09 | **155 复验二轮两症状(br 左上角色块/空白蔓选)修复,v12** | 同源=官方机制没抄全:br::selection 透明规则漏抄;页面空白区可选致拖选焦点蔓上容器。修=补规则+空白 user-select:none+endOfContent 盾片(移植特异性坑见 lessons L19)。实证:边距拖=58 字符单行单矩形;8 手势电池/r3 8/8/PDF 19/19 全绿;v12 已发布待 owner 复验 |
| 2026-10-09 | **三轮收尾 v13:最大化右出界蔓选/行首精度/串台 bug** | 复现条件补全(owner:最大化+右出界);官方 oracle 证实同行为(非移植错);修=命中垫+手动锚定+rAF 帧循环钳制+驱动单例自毁(L20)。测试改零打扰(owner 立规)。合成层污染复现修复后全绿+r3 8/8+PDF 19/19;v13 已发布待 owner 亲手复验 |
| 2026-10-09 | **四轮终版 v14:锚点钉死+全程自驱(反选修齐)** | owner 复验 v13 报"按住划选+空白上下移动→反选";根因=每帧重读 sel.anchorNode 被原生污染放大(L21)。v14:mousedown 钉锚(caretRangeFromPoint)+每帧钳到最近行(跨页)+双击/shift 留原生;单例自毁沿用。零打扰(页面内派发事件)全场景验证+ r3 8/8 + PDF 19/19;已发布待 owner 复验 |
