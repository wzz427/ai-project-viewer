# SPEC-021-MD 图片点击放大(MD 文档里的图,点一下弹大图窗口放大看)

> 状态:唯一真值 = INDEX.md 那一行,本页不抄
> 创建:2026-11-15;Pre-Draft 出处=owner 当日报障式需求(带截图)+方案呈报对话,
> owner 回复「开工」=A2 开工门过(方案全文见对话;硬规矩=方案落纸面经确认才开发,2026-10-31 立规)

## 〇、值不值得做(两栏三出口,一行各一句)

- 好处:owner 日常读 AI 产出的 MD 文档,截图/示意图只能缩在正文列里看(最宽 88ch),细节看不清;每次读带图文档都疼,owner 直接报的需求。
- 代价:小改动(一个弹窗组件+一个三行 store+MD 点击接线);可能碰坏 MD 渲染视图的链接点击链(同容器事件代理)——守卫覆盖。
- 判:值→做。

## 一、Pre-Draft 结论(讨论过了才许写这份文档)

- 核心选择题:方案(弹窗形态/按钮清单/滚轮+拖动/零驻留边界)已呈报 owner;owner 拍板「开工」,无修改意见。
- 标杆对照:Typora/VS Code 预览的图片点击放大;缩放语义与本项目已有的图片文件查看器(spec-003)完全一致。
- **界面确认**:方案落纸面(owner 看过的对话全文)+开工令,2026-11-15。

## 二、需求正文(R 编号;使用者视角)

| R# | 需求(使用者视角) |
|---|---|
| R1 | 渲染视图里,鼠标悬停在普通图片上时光标变成放大镜(提示可点);链接里的图片保持手型(链接优先) |
| R2 | 单击普通图片 → 弹出居中大图窗口(暗色遮罩盖住应用),打开时先按窗口大小完整显示 |
| R3 | 窗口顶部工具栏:适应 / 100% / 放大 + / 缩小 − / 图片实际尺寸读数,右上角 × 关闭;滚轮随手缩放;放大后按住拖动看细节 |
| R4 | 关闭方式:× / Esc / 点暗色遮罩环;关闭后窗口与图片数据全部丢弃 |
| R5 | 图片包在链接里 → 点击走链接(现状不变);显示失败的图(缺失/未加载出)点击无反应,不弹空窗 |
| R6 | 文案走语言切换(中/英),与全应用一致 |

**反例规则(不许做什么)**:不许为弹窗重新读盘取图(直接用正文里已加载的那张);不许驻留(关闭后任何引用不存活);
不许改变独立图片查看器(spec-003)的行为语义;Source 源码模式无图可点,N/A;远程 http 图片本就不显示(CSP),N/A;
Mermaid 图/公式不是 `<img>`,N/A。

**穷尽性清单**:触发器=单击(悬停只变光标)/状态:空(缺失图,见 R5)/边界:切主题、切页签、弹窗开着时文件被 watcher 重载(弹窗独立于页签,不动)/重复点击(开着一张再点另一张=换图重置视图)/撤销:N/A(无破坏性操作)/持久化:N/A(瞬态弹窗)。

## 三、验证标准(V 编号;可判定,直接变测试用例)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | 渲染视图普通 img computed cursor=zoom-in;`a img`=pointer | 自动 |
| V2 | R2 | 点图后出现 [role=dialog] 且其 img src=被点图的当前 src;初始为适应模式(无内联宽度 style) | 自动 |
| V3 | R3 | 点 100% 后图片渲染宽=natural 宽;点 +/− 宽度变化;工具栏五类控件齐(Fit/100%/+/−/×)+尺寸读数随 onload 出现 | 自动 |
| V4 | R4 | 点遮罩环或 Esc 后 dialog 消失;store 状态归零(open=false,src="") | 自动 |
| V5 | R5 | 链接包图点击走既有链接逻辑(不弹窗);缺失图(broken decode)点击无弹窗 | 自动 |
| V6 | R3/R6 | 双主题截图亲验:弹窗形态/暗面衬托图片/按钮可辨/中英文各一张 | 人工 |

## 四、技术实现方案(三步曲 (b):确认后才开发)

- 动哪些文件:
  - 新 `src/lib/components/Viewers/ImageStage.svelte`(从 ImageViewer 抽出的共享缩放舞台)
  - 新 `src/lib/components/Lightbox.svelte`(app 根挂载一次,同 ErrorDialog/LocateDialog 形态)
  - 新 `src/lib/stores/lightboxStore.svelte.ts`(open+src 两个字段)
  - 改 `ImageViewer.svelte`(改用 ImageStage,行为不变,phase3 既有守卫回归)
  - 改 `MarkdownViewer.svelte`(onLinkClick 加 img 分支+cursor CSS)
  - 改 `App.svelte`(挂载)、`app.css`(暗面 token)、版本三处
- 关键取舍:见决策表。

### 决策依据(后续翻案只翻这节)

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 缩放模型抽成共享 ImageStage,ImageViewer 改为其使用者 | 两处(图片文件查看器/MD 弹窗)同一手感,改一处永远同步 | 复制一份 60 行 | 必漂移(AGENTS「改公共的东西绝不补丁式」) |
| D2 弹窗数据源=正文 img 已加载的 src(data URL) | 零额外读盘,点击瞬间开 | 重新 readMediaFile | 白付一次 IPC+解码,内存原则 |
| D3 弹窗暗面独立于两主题(同暗) | 照片查看惯例(VS Code/Windows 照片全用暗面),浅色遮罩伤图片对比度;两主题均浅色,无主题切换必要 | 用 --bg 混色 | 浅纸色垫底时浅色 PNG/截图对比度崩 |
| D4 链接图不弹窗 | MD 语法里图包在链接里=作者要链接导航,弹窗会抢走导航 | 图优先 | 破坏既有链接语义(spec-018) |
| D5 naturalWidth>0 才弹 | 缺失图 decode 失败 naturalWidth=0,弹窗只会是破图占位 | 无条件弹 | 空窗无意义 |
| D6 关闭即清 store(open=false+src="") | 内存第一原则:字符串引用不存活;data URL 本体仍在正文 img 里,弹窗只是借用 | 保留缓存复用 | 零驻留契约(V1.5 §6) |
| D7 零新 i18n 键 | 工具栏文案全复用 viewer.fit/zoomIn/zoomOut/imageControls+common.close | 新增 lightbox.* 键 | 同义文案两处必漂移 |
| D8 弹窗开着时换图=重置回适应模式 | 与切文件重挂查看器(ActiveViewer {#key})同语义 | 保留旧缩放 | 旧缩放对新图无意义 |

**同一条依据已同步写进它管的那段代码的头注释**(依据和它管的东西不许分家)。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | phase3 计算样式断言 | 夹具项目 assets/picture.png+现场建 MD | ✓ md_lightbox_cursor_affordance |
| R2 | V2 | phase3 点击+DOM 断言 | 同上 | ✓ md_lightbox_opens_fit |
| R3 | V3 | phase3 按钮+几何断言 | 同上 | ✓ md_lightbox_actual_and_zoom |
| R4 | V4 | phase3(Esc/遮罩)+vitest store 归零断言 | 无 | ✓ md_lightbox_close_and_refit+vitest×3 |
| R5 | V5 | phase3 链接图+缺失图 | 现场建 MD(链接图+坏相对路径图) | ✓ md_lightbox_edges |
| R6 | V6 | 截图亲验双主题+切语言 | 临时项目 | ✓ 截图×5 视觉模型逐张 PASS(paper-fit/actual/glacier-fit/zoomed/zh-fit) |

回归:phase3 既有 image viewer 守卫(image_to_image_switch/gif_renders 过)+新 image_file_viewer_actual_size(D1 重构行为同一性);Rust 零改动→cargo 免跑;未触树域→freeze-guard 免跑。

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物(矩阵/自检/验收原话) |
|---|---|---|
| 2026-11-15 | Pre-Draft→Draft→Ready→InDev | 方案对话+owner「开工」;矩阵 §五齐 |
| 2026-11-15 | InDev→InTest(0.8.29 已发体验渠道) | 全档:check 0/0+vitest 166/166(+3)+phase3 PASS×2(+6 守卫);截图×5 视觉模型逐张 PASS(glacier-zoomed 首判两条 ❌ 均证伪:遮罩压暗误读+我方提示词预期错,补探针实证 theme=glacier 生效);exe UTF-16 核 0.8.29 FOUND/0.8.28 absent,json 93B 无 BOM;内存账:零新增驻留(store 两字段瞬态槽,关即清零) |
| 2026-11-16 | 返工轮(0.8.30 已发,owner 两报) | ①「放大超 ~150% 画面冻结只剩数字涨」:诊断探针实证 477% 时 styleW=2289.6 但 rectW=1230=面板宽——**flex-shrink 默认 1 把超出容器的图片压回面板宽**(自 spec-003 图片查看器起就潜伏,此前无人放大越过面板);修=ImageStage `.stage img{flex-shrink:0}` 一条(共享组件,文件查看器同愈);守卫补 `md_lightbox_zoom_grows_past_stage`(rectW≈styleW±2 且>面板宽——0.8.29 出门的根因=V3 只测 100% 在面板内+缩小方向,从未断言「长大越过面板」)。②「看图窗口无法通过鼠标移动」:探针实证图片拖动平移可用(放大后按住图拖,translate 精确),缺的是**窗口本体移动**→顶栏作把手拖动整窗(指针捕获+视口钳制留把手,每次打开回居中);守卫 `md_lightbox_drag_pans`+`md_lightbox_window_drag_by_bar`(移动精确±0+重开复位)。全档:check 0/0+vitest 166/166+phase3 **PASS×2**(8 守卫);截图×2 视觉 PASS(477% 真实放大被裁切/窗口拖离中心);0.8.30 已发(UTF-16 核,json 107B 无 BOM) |
