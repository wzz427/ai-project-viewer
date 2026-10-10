# handoff —— 现在在哪 + 上一段为什么这么改

> 给下一个会话(或新人)的交接:**读完就知道"现在在哪、接着干啥"**,刻意短。
> 它不是日记,**更不是待办清单**——"还剩几件"住 debts.md(没有债务表的小项目,
> 待办住台账的"去处"列),这一页只装"发生了什么、为什么"。
>
> **怎么防胖 —— 整批回收,不是逐行削**:① 平时该加就加,别管行数;
> ② 发一版(或页面翻不动了,目测 300 行往上)把这批已完结的**整批蒸馏**进 history/progress/;
> **🚫 绝不"为了加一条删一条"——那样删掉的永远是最好删的那条。行数不设硬顶。**
> **写法**:每条只留"结论 + 下一步 + 去哪看全文";推导、实测原文留在它自己的 SPEC/报告里。

## 〇、现在主线是什么(最先读)

主线 = **spec-006(Phase 6 HANDOFF)InTest 等 owner 复验**:0.6.2 已发体验渠道(2026-10-10),owner 点 Update 后照 spec §六 InTest 行的清单验(三处右键菜单的分型条目/复制路径 toast/Settings 的 VS Code 窗口模式)。**过则 spec-006 转 Done → 下一需求 = Phase 7 Git Review(V1.5 §181)立 spec-007;发版固定 0.6.x 递增(下一发 0.6.3),不跳段。**
遗留小披露(见下条):owner 记事本里留了一个 AIV-TestProject 的 README.md 标签(真机轮所开,手动关即可);教训 L25 已入档(真机轮价值/单实例应用验证法/全局按键红线/phase3 STATE 路径 BEL 事故)。

## 一、现在在哪(最新在上)

### 2026-10-10 · spec-006(Phase 6 HANDOFF)交付:0.6.2 已发,等 owner 复验

> **下一步从哪接** —— owner 点 Update(0.6.2)复验:①文件树右键 README.md→Edit in Notepad(文件真在记事本开=已有窗口新标签)/Open in VS Code/Show in File Explorer/Copy Absolute/Relative Path(toast 确认);②PDF 右键=Open with Default PDF App(无 Notepad/VS Code);html/.url 右键=Open in Browser;文件夹右键=Open Folder in VS Code;③项目标签右键=Open in File Explorer/Copy Project Path/Open Project in VS Code;④Settings 的 Open in VS Code 单选(默认 New Window,切 Reuse 重启仍在);⑤页签右键与树菜单同套条目。全过 → spec-006 Done → Phase 7(spec-007)。

- 交付:Rust `handoff.rs`(§132 ExternalEditor 抽象 Notepad/VSCode+§133 五语义命令,全部 canonicalize 校验,VS Code 探测 Local\**Programs**→PF→PATH)+ 前端共享 `handoffMenu.ts`(树/页签同源防漂)+ 三右键菜单按 §135–141 分型 + §134 VS Code Mode 入持久化;菜单条目随类型变化(文本类无 Open with Default App,图片/系统程序类无 Notepad/VS Code——§142 表为权威)。
- 自测:cargo 63/63、vitest 19/19、check 0/0、phase3 **38/38**(+12 断言)、r3 8/8、pdf-suite 19/19;真机轮四移交实证(notepad 标题/explorer 选中/vscode 新窗/project 打开),浏览器按零打扰跳过。**真机轮抓住 VS Code 探测漏 Programs 段的 bug**(单测喂假目录全绿)——lessons **L25** 三判据+STATE 路径 BEL 事故修复。
- **披露两件**:①真机轮在 owner 开着的记事本里留了个 README.md 标签(Win11 单实例行为,零风险手动关);②一次 Ctrl+W 因前台锁没到达目标窗,疑落入 owner 另一 ZCode 会话(未证实有损)——已立红线:焦点未验证不发全局键。

### 2026-10-10 · 0.6.0 复验打回二轮返工 → 0.6.1 已发;版本规则改 0.6.x 固定递增

> **下一步从哪接** —— owner 点 Update(0.6.1)复验:①MD 最大化文本铺满、右侧无空白带;②所有查看器操作栏同高(MD/代码/JSON/PDF);③上轮工具栏字号/Find/Ctrl+F。过则 INFRA-002+003 一并 Done → Phase 6(V1.5 §180)立 spec-006。**发版从此固定 0.6.x 递增(0.6.1 已用),不跳段,直到 owner 另有指令(D7)。**

- owner 打回两条:①MD 右侧空白仍明显(0.6.0 只做了"860 列居中",断言也是"居中"——修法自证,教训 **L24**:断言必须对着 owner 原话写,"空白明显"的判定=文本块铺满文本区);②操作栏高度不一致=code-host/.host/.source-host 旧 8px 垫高(L24 判据②:统一类 UI 需求断言必须跨组件比 y/高)。
- 0.6.1:MD 上限删除铺满 + 三处垫高删除 + 断言 `md_text_fills_area`/`toolbar_aligned_md_vs_code`;phase3 26/26、r3 8/8。→ **owner 同日"收口吧"放行,INFRA-002+003 转 Done(验收原话记入 INDEX);architecture §3 代码地图已补 ViewerToolbar/activeFind;V1.5 §197 已加 0.6.1 翻案行(上限删除)并在旧行留指针。**

### 2026-10-10 · "最大化后切换空白"排查收口(未复现)+ 0.6.0 统一操作栏交付,等 owner 复验

> **下一步从哪接** —— owner 点 Update(0.6.0)复验:①MD/代码/JSON 顶部操作栏(A−/A+ 字号、Find 计数+上下条跳转);②Ctrl+F 聚焦当前查看器查找框(PDF 同);③MD 最大化阅读列居中不再右侧空白;④顺带确认上轮图标三处。全过则 INFRA-002+003 转 Done → Phase 6(V1.5 §180)立 spec-006,发版 0.7.0 起。

- **"切换空白"案(owner 13:37 报障,前会话 0.5.0 之后)**:三路合成复现(Emulation 视口/真实拉宽/最小化恢复)全不现;中性复读截图纠偏(先前视觉分析被我的提示词带偏,误报页签名);**owner 亲手复现+CDP 全程监测零异常** → 判疑似更新重启首会话偶发,未复现不硬修;main.ts 装全局错误哨(window error/unhandledrejection→console)再犯留名。教训 **L23**:几何/挂载类改动回归必含"resize→跨类型切换"(已补 phase3 `resize_then_cross_type_switch`);发版前必核三处版本号是自己的段(前会话提交写 0.4.2 实发 0.5.0=图标段号,段号冲突已发生)。
- **0.6.0 交付(SPEC-INFRA-003)**:新 `ViewerToolbar.svelte`(字号=全局 §22 同一旋钮;Find=页导航级计数+跳转,同 PDF 先例)+ `activeFind.ts` 注册表(Ctrl+F 统一,CM 面板回退);Code/Json 经 CodeViewer 自带工具栏,MD 渲染态自挂(源码态由内嵌 CodeViewer 提供);PDF 只注册搜索框不动工具栏;MD `.rendered` margin:auto 居中(860px 上限保留)。
- 自测:vitest 19/19、svelte-check 0/0、phase3 **25/25**(新增 8 项)、r3 8/8;V1.5 §197 审计行已落;0.6.0 三处版本号已核。

### 2026-10-10 · 0.4.2:文件树层级竖线 + PDF 窗口变大不回填修复

> owner 截图两问:①树无隶属指示→加 VS Code 式 indent-guide(每祖先级一条 1px 竖线,对齐该级折叠箭头;DOM 断言 0/1/3 层=0/1/3 条@14/28/42px);②右侧宽空白→**定性为真 bug**:挂在滚动容器上的 onresize 在 div 上是死代码(resize 事件不触发于元素),窗口从小变大后 fit-width/fit-page 不再重算(owner 状态里 zoom=1.725 对不上最大化窗口≈2.1 为证;视口 1018→2138 画布钉死 971 复现)→修=ResizeObserver 观察滚动区(视口 2400→画布 2091 贴合)。回归:pdf-suite 19/19+phase3 PASS+r3 8/8。0.4.2 已发布,复验清单并入 0.4.1 那批。

### 2026-10-10 · 换图标交付:0.5.0「项目检视」已发体验渠道,等 owner 复验

> **下一步从哪接** —— owner 眼见确认:桌面/任务栏/托盘三处均显示新图标(桌面/任务栏的显示缓存问题已现场修复,见下)→ 过则 SPEC-INFRA-002 Done,按 V1.5 §180 立 spec-006(Phase 6 HANDOFF)开工,发版 0.6.0 起。

- owner 从 A/B/C 三候选选 B(原话"选B";视觉评审 B 小尺寸抗缩最佳、暖色在蓝紫任务栏中辨识度高,A 24px 以下糊被弃)。
- 交付:母图 `src-tauri/icons/icon.png` + 生成脚本 `scripts/make-icon.py`(4096 超采样降 1024);`pnpm tauri icon` 全套重生成(顺手生成的 android/ios 移动端目录已删,纯 Windows 桌面用不上);托盘走 `default_window_icon` 随构建自动换;版本三处 0.5.0。
- 验证:exe 内嵌图标抽取比色 4 点全中(255,140,0 橙 / 255,76,59 红 / 11,17,90 放大镜深蓝);update.json=[0.5.0|2026-10-10 12:56]。同轮 spec-005+INFRA-001 收口 Done(原话"0.4.1 已经过了")。
- **复验报障已处置**(同日下午):owner 报"桌面/任务栏旧图、托盘已变"→ 分层诊断(exe 内嵌=新 / SHGetFileInfo 解析=新 / 画面=旧)= Explorer 显示缓存不重画;SHChangeNotify 广播实测无效,**重启 explorer+清 iconcache_*.db** 后截屏视觉复核三处全新。教训+判定不做(应用内自动刷新)入 **lessons L22**;凡发图标资产,update note 必带"重启资源管理器"提示。

### 2026-10-10 · 会话收尾交接(owner 将开新对话进下一需求)

> **新会话第一件事**:先向 owner 催 **0.4.1 复验**(他点更新后:①划选→按住→右侧空白上下移动不反选;②行首偏左起选;③双击选词;④最大化右出界;⑤托盘行为[✕隐藏/单击恢复/右键 Exit];⑥v8 欠项[更新按钮最右/任务清单光标/右键 Copy])——全过则 **spec-005+INFRA-001 转 Done**,然后按 V1.5 §180 立 **spec-006(Phase 6 HANDOFF)** 开工。**下一需求发版从 0.5.0 起**(版本号规则:一需求一段,见 SPEC-INFRA-001)。
>
> - 本会话交付:PDF 划词四轮终版(0.4.0/0.4.1,内核 155 升级+驱动自驱);版本号 0.xx 制;pdf-guide.md;testing.md 重写+scripts/e2e 全量入库(跑法在其 README);指南测试章增补**建议**(docs/AI-Project-Guide-revision-proposal.md 10-10 节,**改不改由 owner 定**;桌面主本未动)。
> - 知识入口:PDF 问题→docs/pdf-guide.md;测试怎么跑→testing.md §1;划词机理→lessons L17–L21。
> - ⚠️ 多会话:docs/AI-Project-Guide/ 的 6 个未提交修改归另一会话,**勿动勿提交勿还原**。
> - 备份 remote 仍未建(owner 亲手,V1 验收后);V1.5 §196 附注 A 合入排在 Phase 7 前。
> - 会话结束核查已做:工作区仅剩上述 6 文件;无开发实例残留进程;wrap-todo 空。


### 2026-10-10 · 指南测试章"增补建议"落档(owner 纠偏后;桌面主本未动)

> 评估结论"骨架对、操作层缺"→ **建议全文按既有格式追加进 docs/AI-Project-Guide-revision-proposal.md(2026-10-10 增补:建议 4=03-testing 新增§三交互类验证与测试装置[输入分层 L1–L4/升权规则/装置排查清单/oracle/资产纪律+零打扰];建议 5=templates/testing.md §0b;建议 6=连带引用)**,改不改、何时改由 owner 定。**教训入档:中途我曾误解指令直接改了桌面主本四个文件,已全部还原并核零残留——指南真源的修改权不在本会话,建议类产出只进建议文档。**

### 2026-10-10 · testing.md 整体重写 + 脚本全量入库(owner 指令"不能用临时的")

> 在昨日正典化基础上做彻底:testing.md **全文重写**为"手册区 §0–§3(档位/环境/零打扰规程/脚本清单)+ 历史账本 §4(按 Phase 重组,旧 %TEMP% 脚本名全部标注'现行对应/未存档规格')";脚本侧新增 **phase3-suite**(自启动外壳补齐后 17 项全过)、**make-fixtures.py**(夹具生成器重建,扫描件 14MB 达标)、real-input-battery 换前台守卫双模式版;pdf-suite/acceptance-r3 从仓库路径复跑 19/19、8/8 验证。四个已蒸发的历史基建工具(cdp 注入/picker/confirm/shot)在 testing.md §3 记录能力去向与重建配方。

### 2026-10-10 · 测试体系正典化:scripts/e2e 入库 + testing.md 重构(owner 点头+追问)

> owner 问"全场景测试脚本是什么/testing.md 是不是有严重问题"→ 诊断:①testing.md 是编年史不是手册;②脚本全在 %TEMP% 随时蒸发;③零打扰终态埋在轮次记录里。重构:**§1.2 零打扰规程+§1.3 脚本清单上移最前;历史区打横幅"账本不是手册"**;正典脚本入库 `scripts/e2e/`(pdf-selection-battery/pdf-suite/acceptance-r3/real-input-battery+oracle+README)。pdf-guide §4/§6 同步指向;挂账"Playwright 入库"销账。


### 2026-10-10 · docs/pdf-guide.md 建立(owner 指令:沉淀 PDF 处理经验给未来 agent)

> owner 问"这次划词为什么这么费时间,有没有深入总结"→ 全程复盘落成 docs/pdf-guide.md:架构现状/pdf.js 硬知识/选择机理六条/验证规程七条/六轮战史(症状→误判→真因)/未来检查清单。**总账:六轮里真代码错只有 1.5 轮,其余=内核缺陷/仪器错误/移植欠账/半吊子设计。** AGENTS.md 路由表已加行(PDF 活→先读它)。


### 2026-10-09 · 版本号改制 0.xx(0.4.0 已发布,内容同划词终版)

> **owner 拒绝 vN 递增编号**(一天 v14 太荒唐),拍板 0.xx 制:一个需求一段(本需求 0.4x,下个需求 0.50,全齐升 1.0.0)。已落地:tauri.conf/package.json/Cargo.toml=0.4.0;publish-experience.ps1 自动读版本前缀到 note;update.json 现为 `[0.4.0 | 2026-10-09 22:07] 划词终版…`。规则全文在 SPEC-INFRA-001。
> **0.4.1 已跟进**:owner 反馈悬停看不到版本——note 原本只在"有更新"时显示;现构建期从 package.json 注入,悬停**常显** `Version 0.4.x — you are on the latest build`(有更新时附说明)。r3 8/8。

### 2026-10-09 · 划词终版(=0.4.0;owner 复验 v13 报"空白区上下移动反选";重写自驱)

> **下一步从哪接** —— **等 owner 点更新到 v14 亲手复验**:①按住划选→移到右侧空白上下移动→选区始终=锚点到最近行,不反选不蔓选;②最大化右出界/行首起选/双击选词/跨页拖选;③连 v8/v10/v12 欠项。全过则 spec-005+INFRA-001 收口进 Phase 6。

- 根因(v13 残留):驱动对原生手势每帧重读 `sel.anchorNode` 当基准,原生在无字列把锚点拖到文档边缘后污染被放大(L21);**v14=锚点按下即钉死+全程自驱+每帧钳到最近行(跨页支持),双击/三击/shift/键盘留原生**。
- 验证(零打扰,页面内派发事件驱动——绕开可信合成输入被吞的盲区):owner 原场景 60c/1L 锚点稳;远端上移/左右出界/行首/跨页/双击/污染全对;r3 8/8;PDF 19/19。v14 已发布。
- 划词至此四轮:内核(155 升级)→左上角色块(br 透明)→出界蔓选(钳制)→反选(自驱)。教训链 L17→L21 完整入档。

### 2026-10-09 · v13:划词三轮收尾(最大化右出界蔓选/行首精度/串台),测试改零打扰

> **下一步从哪接** —— **等 owner 点更新到 v13 亲手复验**:①最大化窗口划到行尾继续往右拖→只选到行尾不蔓选;②行首左侧 20px 内可直接起选;③连续多种划法混合用不再互相污染。连 v8/v10/v12 待复验项一起过则 spec-005+INFRA-001 收口进 Phase 6。

- 机理定论(官方 oracle 对比):pdf.js span 无行盒,文字侧空白列无选择 quad,Chromium 延伸落文档起点=蔓选,**官方查看器同行为**;修成 Adobe/Chrome 体验=20px 命中垫+手动锚定+rAF 帧循环钳制(L20)。
- 串台 bug:垫内起选的驱动残留会用下一手势指针续写旧锚点选区(146c 数字对账定位);修=驱动单例+8s 自毁。
- **owner 立规(晚):测试永久改零打扰**——AIV_HIDDEN+屏幕外窗口+CDP 合成输入,不许再抢鼠标/弹窗;合成盲区(垫起选全程、拖选中 move 被吞)留 owner 亲手复验。此规已入 testing.md §4+L20。
- 回归:合成层污染复现→修复后全绿;r3 8/8;PDF 19/19;宽屏右出界 38c/1L。内存账:每手势 3 个窗口监听+1 个 rAF 循环,松手/自毁即清,零驻留。

### 2026-10-09 · v12:155 复验二轮两症状收尾(br 色块/空白蔓选),已发布

> **下一步从哪接** —— **等 owner 点更新到 v12 复验**(更新按钮应已亮):①选行时左上角无色块;②拖选进入文本外侧空白,选区停在文本内不整页蔓选;顺带 v8/v10/v11 待复验项。全过则 spec-005+INFRA-001 收口进 Phase 6。

- 两症状同源=官方查看器机制没抄全,非内核:①`br::selection` 透明规则漏抄(br 全叠层左上角,选中亮成色块);②页面空白区可选(继承 .viewer-body),拖选焦点蔓上容器=整页选——修=空白 user-select:none+span 自行恢复+官方 endOfContent 盾片。
- **移植坑入 L19**:官方 css 靠等特异性+源顺序压层序,scoped 选择器翻转了它,盾片一度盖住全部命中(选择死锚点);修=补足 `.pdf-text-layer > .pdf-end-of-content` 特异性。
- 实证:行内→边距拖=58 字符单行单矩形;8 手势电池全绿;r3 8/8;PDF 19/19。内存账:每渲染页 +1 空 div、每查看器实例 +2 个窗口监听(卸载即清),无新驻留。
- 测试侧:拖选出窗口会触发选区自动滚动污染读数(落点限窗口内);真实输入测试连吃三次"结果漂移"全是我方脚本坐标/前台/场景问题(L18/L19)——**owner 症状永远优先于脚本读数**。

### 2026-10-09 · 划词问题闭环:owner 选 A,Runtime 升 155,app 实测全绿

> **下一步从哪接** —— **等 owner 复验(把 app 完全退出再重开,运行中的旧实例还挂着旧内核)**:PDF 划一行只选一行(左右方向都试)、双击选词、右键 Copy;连 v8/v10 待复验项一起过则 spec-005+INFRA-001 收口进 Phase 6。

- **A 已执行**:Evergreen Runtime 143→155.0.4283.45(离线包+管理员;引导器/winget 静默装因 per-machine 无提权报 0x80040828,坑记 lessons L18)。app 无需发新版,重启即吃到新内核。
- **实测判决**(真实输入层,testing.md §4):官方对照页与 app 同电池 8 手势**逐项打平全绿**——长拖 1 行不蔓延、右往左拖 ✓、小拖 ✓、双击选词 'brown' ✓。
- 调查途中揪出**验证层自己的两个坑**(L18):DPI 虚拟化坐标错 1.25 倍(假"蔓选")+ 前台被聊天窗口抢走(假"全死")——都进了公式修正与前台守卫,`%TEMP%\aiv-battery-replica.py` 可复跑。
- 本机 EdgeUpdate 自动更新停摆(Edge 停 140):再遇内核问题手动升级运行时(方法在 testing.md §4)。

### 2026-10-09 · 主线现状:PDF 划词阻塞在 WebView2 内核,等 owner 选 A/B(wrap 落盘)【已解决,见上条】

> **下一步从哪接** —— **owner 拍板 A/B**:A=升级 WebView2 Evergreen Runtime(推荐,零代码,微软官方装完即好)/ B=自实现选择层(约 1 天)。定 A 则装完让 owner 在 v11 直接复验;定 B 则按 testing.md §4 的真实输入层为验收标准开工。**另:spec-005 与 INFRA-001 的 owner 复验一直累积未做(v8 四项/v10 托盘/v11 划词),下次对话先催复验再开新活。**

- 本日三件已交付:v10 关窗=系统托盘(owner 澄清目标);v11 PDF 文本层官方对齐(Chrome 下完美);验证体系 v2(testing.md §4:真实输入层+官方对照层,owner 质疑后立)。
- **PDF 划词定论**:证据链闭合——官方对照页在 Chrome154=完美/本机 WebView2=蔓延,**WebView2 文本选择内核缺陷,v11 代码无罪**;本机 WebView2 目录 140/143 共存、生效版本未确证(症状同 140)。详细数字与换算方法在 testing.md §4。
- Phase 6(HANDOFF)未开工,排在 spec-005/INFRA-001 收口之后。

### 2026-10-09 · PDF 划词蔓延修复(textLayer 官方对齐),已发布 v11

> **下一步从哪接** —— owner 更新 v11 复验:PDF 里划一行只选一行、右键 Copy;连 v8/v10 待复验项一起过则 spec-005+INFRA-001 收口进 Phase 6。

- 根因:textLayer span 的字号/定位依赖官方 CSS 变量链(--total-scale-factor、font-size calc、transform rotate/scaleX)——首版只抄了一半,span 盒子与字形完全脱节,选择矩形落错行。修:容器设 --total-scale-factor=scale、span 官方规则全量、canvas 升级高清渲染(dpr,官方配方)。
- 实证:单行拖选 54 字符 1 行;回归 r3 8/8(拖选改从真实 span 盒出发,比例坐标会落行间隙)+PDF 19/19;v11 已发布。

### 2026-10-09 · 关窗行为修正:隐藏到系统托盘(owner 澄清),已发布 v10

> **下一步从哪接** —— owner 更新到 v10 复验:✕ → 窗口消失、图标在系统托盘(时钟旁);托盘单击恢复;托盘右键 Exit 真退出。连 v8/v9 待复验项一起过了则 spec-005+INFRA-001 收口进 Phase 6。

- owner 画图澄清:初版"最小化到任务栏主区"不是他要的——目标是**系统托盘**(通知区)。实现:CloseRequested=prevent+hide(主任务栏不占位);托盘图标(Tauri 2 tray-icon)单击恢复/右键 Show+Exit;Exit=app.exit→RunEvent::Exit→状态兜底落盘。
- 实证:✕(WM_CLOSE)→隐藏+存活 ✓;隐藏后二次启动→single-instance 恢复窗口 ✓;退出落盘 ✓(托盘菜单 Exit 为纯 UI 入口留 owner 复验,逻辑与已测路径同源)。cargo 52/52;V1.5 §16 修正+§197 审计;v10 已发布。

### 2026-10-02 · 新需求:关窗=最小化到任务栏(V1.5 §16 增量修订),已发布 v9

> **下一步从哪接** —— owner 更新到 v9 复验:点窗口 ✕ → 最小化到任务栏(进程活);任务栏图标右键 →"关闭窗口" → 真退出。连同 v8 四项一起复验过则 spec-005+INFRA-001 收口进 Phase 6。

- 规则(V1.5 §16 增量修订+§197 审计):**可见状态收到关闭请求=最小化;已最小化状态收到关闭请求(任务栏右键"关闭窗口")=真退出**——两种请求系统层面不可区分,按窗口状态分派;拦死 close 会让任务栏菜单失效、应用只能任务管理器杀。
- 实证(WM_CLOSE 真路径):最小化收关闭→退出+状态兜底落盘 ✓;可见收关闭→最小化+存活 ✓(JS window.close() 在最小化窗口的时序差异不影响用户路径,备注 testing)。cargo 52/52;v9 已发布。

### 2026-10-02 · 验收三轮四修:按钮位置/PDF 文本层/列表光标/右键复制,已发布 v8

> **下一步从哪接** —— owner 在体验版点 Update 升到 v8 → 复验四项(顶栏最右按钮/PDF 划词复制/任务列表光标/右键 Copy)→ 过则 spec-005+INFRA-001 一并 Done,进 Phase 6。

- 四修全部自动化实证(8/8):Update 按钮顶栏最右(+ 按钮留在标签旁);**PDF 文本层**(owner 报"PDF 划词无效"=确认要选字,D5 原判被翻,透明 span 对齐字形,选择/高亮/右键复制全通);任务列表 label/checkbox 光标修复(form 控件不继承 cursor 是根因);查看器右键 Copy(有选区才弹;菜单冒泡关闭竞态已修)。
- 防退化:PDF 19/19+P3 PASS;v8 已发布(publish-experience.ps1,note 含本轮改动)。

### 2026-10-02 · SPEC-INFRA-001 体验版+更新机制落地,等 owner 首次点更新复验

> **下一步从哪接** —— owner 完全关闭旧客户端 → 双击桌面快捷方式(=体验版,⚠️ 必须关旧的,这是最后一次"完全重启")→ 右上角 Update 高亮 → 点击 → Restart Now → 新版生效(Channel=experience/Build 时间)。之后每轮交付我只 publish+通知,他点按钮即可。**spec-005(PDF)仍挂 InTest 等他在体验版上复验**;PDF 内选字待表态。

- 交付流程改版(testing.md §2f):owner 客户端独立(.exp identifier/目录/数据,已装机+state 已迁移+快捷方式已重指);我每轮 `scripts/publish-experience.ps1 -Note "..."`;updates 当前=v6(与已装相同→首次打开按钮即灰?**不**——已装=v6、updates=v6 → 灰;owner 复验路径:我 publish v7 后他点亮体验)。
- 更新机制:md5 内容判定+rename 自替换+启动清理;回归 8/8+防退化全绿;TaskDialog 无子 HWND(L7 补记)→ test_mode_active 跳原生确认;PS BOM 坑双端修(L2 家族)。

### 2026-10-02 · Phase 5 验收二轮:opener scope 真机修通+I-beam+页签宽,等 owner 复验

> **下一步从哪接** —— owner 复验(完全重启应用:右键 txt/PDF → 系统程序真打开;内容区 I-beam 可划选;长名页签封顶)→ 过则 Done、立 spec-006(Phase 6 HANDOFF);**PDF 文本层(画布内选字)待 owner 表态**。

- 右键 Not allowed 根因=opener 第二层门 scope 默认空(capability 权限≠scope,lessons L16);修复后**真机实证记事本弹出打开**——外联功能验证标准从"handler 执行"升到"真程序弹出"。
- I-beam 光标、长名页签 160px 封顶+省略号;回归 PDF 19/19+P3 PASS;release 已重建。

### 2026-10-02 · Phase 5 验收轮返工:引擎卸载/文本选择/右键三修,等 owner 复验

> **下一步从哪接** —— owner 复验(testing.md §2e 末尾返工段:完全重启应用→选字/右键/PDF 全流程)→ 过则 Done、立 spec-006(Phase 6 HANDOFF);**PDF 文本层(画布内选字)待 owner 表态**,要则约半天(textLayer 对齐)。

- 三修:① 引擎卸载改"关最后一个 PDF 页签即归零"(每文档独立 worker+关尾 terminate;**连带修 pdfjs destroy 连环哑炮**——先关 A 后 B 永挂,lessons L15);② 文本不可选=body 全局 user-select:none 盖查看器,.viewer-body 恢复 text;③ 树右键 Open with Default App 无反应=L12 同族漏网,快照先行(L12 补记:按菜单族扫)。
- "点 PDF 没显示"复现排查:owner 真实 state+当前 release exe 实测正常,判定为旧实例(单实例激活旧窗);已嘱完全重启。
- 回归:修复 6/6+PDF 19/19+P3 PASS+P4 24/24+cargo 49/49+vitest 19/19;release 已重建。

### 2026-10-01 · Phase 5 交付:PDF 查看器全功能,自测全绿等验收

> **下一步从哪接** —— owner 验收(testing.md §2e 末尾:开 PDF/工具栏/搜索/深滚/切回恢复/扫描件/重启还原)→ 过则 Done、立 spec-006(Phase 6 HANDOFF)。

- 交付:PDF.js 查看器全套(§92 十项工具栏+§93 状态恢复+§95 虚拟化+§96 切离释放+§98 Benchmark);字节通道 read_binary_file(ArrayBuffer,100MB 顶);CSP 仅加 worker-src 'self' blob:;pdfState 随 Phase 4 白名单持久化(重启还原页码/缩放/滚动)。
- **spike 最大发现:pdfjs 6 必须用 legacy build**(modern 对原生 Map 调 getOrInsertComputed——upsert 提案 API,WebView2 143 没有;另修 Svelte 连坐两坑,lessons L14);搜索为页导航级(D5:命中计数+跳页,字符级高亮不做——owner 要再加)。
- Benchmark 判读(testing.md §2e):开一个文本 PDF ≈ +134MB;100 页≈10 页(虚拟化生效);5 Tab 仅 +340MB(**不线性吃 RAM** ✓);数字含 CDP 底座口径已注明。
- 自测:cargo 49/49、vitest 19/19、check 0/0、CDP PDF 回归 19/19(debug+release 双跑)、防退化(P3/P4 全绿);夹具 `AIV-TestProject\pdf\`(生成脚本 %TEMP%\aiv-p5-make-fixtures.py);release 已重建。

### 2026-10-01 · Phase 4 全闭环;spec-005(Phase 5 PDF.js Spike)立项开工

> **下一步从哪接** —— 按 specs/spec-005 §六切分开发:块①spike 实测(Asset Protocol/Worker/CSP 三路线决策)起。

- owner"可以了"=侧栏拖拽复验通过,Phase 4 全闭环(Done+追加件)。
- Phase 5 范围(V1.5 §179/§91–98):spike 验证(Asset Protocol/assetScope/Local PDF/Worker/CSP worker-src+img-src/md 本地图片/Worker Lifecycle)→ Load→Worker→Render One Page → 完整 UI(§92 十项)→ 虚拟化/搜索/缩放 → benchmark(§98 四场景)。
- 新依赖预告:pdfjs-dist(npmmirror);PDF 夹具(benchmark 用 10 页文本/100 页文本/100 页扫描)待生成。

### 2026-10-01 · Phase 4 交付:会话恢复+设置持久化,自测全绿等验收

> **下一步从哪接** —— owner 验收(testing.md §2d 末尾 1.5 分钟路径:加项目→展开/Pin/开页签→改主题字号→关掉重开看还原)→ 过则 Done、立 spec-005(Phase 5 PDF.js Spike)。

- 交付:关掉重开一切还在——项目标签、展开目录、置顶收藏、文件页签(含激活页/Rendered|Source/固定状态)、侧栏所在面板、主题/字号/两个树开关;写盘 800ms 防抖+tmp→flush→原子替换,退出前端 pagehide+Rust Exit 双兜底;state.json 损坏→自动隔离备份+全新启动不崩;测试态(AIV_TEST_PROJECT 无 AIV_STATE_FILE)永不在 owner 的 state 上读写。
- **开发中发现真 bug:contentCache 原为 `$state(new Map())` 零响应性**(Svelte 5 深代理只包 plain object/array)——恢复页签永久卡 Loading,正常开文件一直正常纯属时序巧合;换 SvelteMap 修复(lessons L13,坑自 Phase 3 就埋着)。
- 基线对齐三件(spec-004 决策表 D5/D6/D8):showSystemFolders 挪全局(§22 字面)、sidebarMode 入每项目会话(§17 字面,切项目恢复各自面板)、字号入 AppSettings.viewer.fontSize(V1.5 §22 增量修订+§197 审计行已落)。
- 代拍默认两项待 owner 过目:sidebarWidth 持久化就绪但**无拖拽调宽 UI**(V1.5 无交互明文,要即加);恢复 5–20MB 页签**不弹确认**(§106 针对用户打开动作)。
- 自测:cargo 48/48、vitest 18/18、svelte-check 0/0、CDP 持久化回归 24/24、Phase 3 回归 17/17 防退化;脚本 `%TEMP%\aiv-p4-state-test.py`(AIV_STATE_FILE 指独立文件);release 已重建。

### 2026-10-01 · 会话收口:spec-003 Done,交接给新会话做 Phase 4

> **下一步从哪接** —— 新会话按 AGENTS.md 开机三步进来 → 读本页 → 立 spec-004(Phase 4)→ 免审开工。

- **owner 协作习惯(本会话实证)**:高频验收、反馈以编号列表来;测试**绝不许抢前台/闪窗**(硬规矩,testing.md §1 零前台启动式);要求"说人话";每 Phase 完成即停等验收,他会快速试用并打回细节——预留返工轮次是常态。
- **需求基线已被修订**:V1.5 尾部 §197 增量修订审计(排序合一/⋯ 并入 Settings/固定页签模型/Open with Default App 等)——查需求时**必须看 §197**,别按旧原文实现。
- **测试基建(零前台)**:`AIV_HIDDEN=1 AIV_TEST_PROJECT=<夹具> WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9222 <exe>`;脚本在 %TEMP%(aiv-p3-fix-test.py 回归 17 项/aiv-p3-read-test.py 全套/aiv-picker.ps1);**夹具=桌面 `AIV-TestProject`(owner 验收用,勿删)**;`aiv-test-projects\TreeAlpha` 可删;隐藏窗口收不到可信键盘→DOM 合成 keydown(L11)。
- **工作树警示**:`docs/AI-Project-Guide/` 下 6 个文件是**另一会话(改指南的 agent)的未提交改动**,不是本会话的——别提交也别回滚,留给那边收尾。
- 拖拽三连坑全修完(L10:dragDropEnabled/dragenter+dragover/before-after 双语义+空白带落点);菜单"点了没反应"=act 先执行后 onclose(L12);图片路由=扩展名先于二进制判定(L12)。
- 挂账未动:Playwright 脚本正式化入库(等 owner 点头);备份 remote(owner 亲手,V1 验收后);V1.5 §196 附注 A(Phase 7 前)。

### 2026-10-01 · Phase 3 十项反馈返工:两根因+预览页签+视觉,回归 16/16

> **下一步从哪接** —— owner 复验(testing.md §2c"十项验收反馈返工"末尾 1 分钟路径)→ 过则 Done、进 Phase 4(先立 spec-004)。

- 两个真根因:①内容不刷新=缓存非响应式+同型查看器不重挂载;②图片看不了=二进制判定先于图片路由(JPEG 天然含 NULL)。均修复并有回归用例。
- 新交互:固定页签模型(默认正常累积,Pin Tab 后新文件顶替未固定槽,§186 P1 提前;VS Code 全预览首版被 owner 否,当日改口)+页签右键菜单(模式切换/Keep Open/Open with Default App)+拖拽重排+激活滚入;视觉:白底阅读面/字体栈/字号设置。
- 菜单"点了没反应"根因=onclose 先卸载导致闭包读 prop 抛异常吞 handler(L12,动作先行)。回归 17/17(零前台);V1.5 §197 审计 4 行(第 3 行含改口);release 重建。

### 2026-10-01 · Phase 3 交付:File Tabs+五查看器+五快捷键,自测全绿等验收

> **下一步从哪接** —— owner 用桌面 `AIV-TestProject` 验收(testing.md §2c)→ 通过后立 spec-004(Phase 4)。

- 交付:树单击开文件(D1)→ File Tabs(去重/切换/恢复);Markdown(Rendered|Source、GFM、本地图片 data URL、内链开 Tab/外链浏览器)、Code(CodeMirror 只读+高亮+Ctrl+F)、JSON(Formatted|Source)、Image(缩放/平移,SVG 安全上下文)、守卫(binary/huge/5–20MB 确认)+删除态;五快捷键真行为(Ctrl+R 不 reload=§147 正式验收条款,已断言)。
- 零前台测试模式落地(owner 二次投诉"窗口闪现"后):`AIV_HIDDEN=1`(窗口全程不显示)+`AIV_TEST_PROJECT`(自动加项目免原生框),正常启动不受影响;隐藏窗口收不到可信键盘输入→DOM 合成 keydown 测 dispatcher(testing.md §1 已记)。
- 自测:cargo 38/38、vitest 10/10、svelte-check 0/0、Playwright 全套 30/31(utf16 检查一次偶发竞态,Tab/内容/时序三重人工验证过);release 已重建。

### 2026-10-01 · spec-002 Done;spec-003 立项 Ready

> **下一步从哪接** —— 按 specs/spec-003 §六切分⑧块开发(重点决策 D1 单击即开/D3 图片 data URL/D4 超大占位)。

- spec-002 验收原话入档(InTest→Done);spec-003 Basic READ(File Tabs+五查看器+五快捷键+大文件闸+删除态)按 SPEC 模板立,R/V 指针化,决策 D1–D8,PDF 明确划给 Phase 5。
- 新依赖预告:markdown-it(+task-lists)、CodeMirror 6(npmmirror 可取);Rust 新命令 read_text_file/read_media_file 复用 Phase 2 流水线。

### 2026-10-01 · 二轮反馈:拖到最顶修复 + 测试零前台立规

> **下一步从哪接** —— owner 复验(重点:置顶项**甩到最顶**和**拖到最底**)→ 过则 Done、进 Phase 3(先立 spec-003)。

- "拖不到最顶"根因两层:第一行上方约 30px 空白带(路径框+间隙)不接 drop;WebView2 要求 **dragenter 也 preventDefault** 才发 drop(lessons L10 补记)。修复=置顶行上/下半分插前/插后(顺带能拖到最底)+ 面板顶部区接"甩到顶"+ 行/面板双挂 dragenter/dragover。
- 验证改 **Playwright connect_over_cdp**(pywork):输入走 CDP 管道,应用 SW_SHOWMINNOACTIVE 最小化不激活,三场景(甩顶/最底/行内)全 PASS——**测试脚本从此禁止抢 owner 前台**(owner 立规,testing.md §1 已记)。
- V1.5 §197 审计加行(§39 落点语义细化);spec-002 D11;release 已重建。

### 2026-10-01 · Phase 2 验收反馈返工:排序合一/真拖拽修复/⋯并入 Settings

> **下一步从哪接** —— owner 复验(30 秒路径 testing.md §2b"验收反馈返工")→ 过则 Done、进 Phase 3(先立 spec-003)。

- owner 三条全落地:① 排序合一(Pinned 区+Unpinned 区单一排序制,V1.5 §33 增量修订+§197 审计);② 拖拽根因 = Tauri Windows 默认 `dragDropEnabled` 劫持 HTML5 DnD,配置置 false,**真实鼠标**(mouse_event)实测换序成功——CDP 合成 DragEvent 曾假阳性(lessons L10);③ ⋯ 菜单删除,Folders First/Show system folders/Refresh 住进 Settings 的 File Tree 区,⚙ 点进再点回 Files。
- vitest 重写 10/10、svelte-check 0/0;V1.5 §30/§33 增量修订+§197 审计表;release 已重建(桌面快捷方式自动最新)。
- owner 两问已答(收在会话汇报):Folders First 不勾=非置顶区文件文件夹混排按名;Refresh=重读已展开层并做 Pin 对账(实时监听是 Phase 9)。

### 2026-10-01 · Phase 2 交付:文件树/收藏/文件识别,自测全绿等验收

> **下一步从哪接** —— owner 验收(testing.md §2b 末尾)→ 通过后立 spec-003(Phase 3 Basic READ)。

- 六块全落地:Rust `list_directory`(单层+§29 打标)/`inspect_file`(§101 流水线,encoding_rs)→ 前端 fileTreeStore(相对路径身份)+treeSort 纯函数 → FileTree/TreeItem 懒加载树 + §30 ⋯菜单 + Pin 右键 + 同父拖拽 + Refresh rename 对账(1:1 才算可靠识别)。
- 自测:cargo 32/32(新增 24)、vitest 9/9(新引入)、svelte-check 0/0、CDP 全链(懒加载/可见性/两种排序/Pin 混排/拖拽/rename 保位/delete 清 Pin/磁盘 md5 前后对比 PASS);fixture `aiv-test-projects\TreeAlpha`(含 GB18030/二进制/5MB/21MB,用后可删)。
- release 已重建,桌面快捷方式自动最新;spec-002 增补 D9(树默认偏好 Name+Folders First,§17 未定取 VS Code 惯例)。
- 拖拽手感与 ⋯ 菜单视觉留 owner 手测;inspect_file 的 UI 消费(编码状态栏/Large File 确认框)按计划随 Phase 3 第一个 Viewer。

### 2026-10-01 · specs 体系对齐指南;owner 拍板 Spec 免审

> **下一步从哪接** —— 直接按 specs/spec-002 开工(六块提交切分),**不用再等 owner 点头**;动笔前有疑问/要变化先确认(workflow §五 A2)。

- owner 拍板三件:① **Spec 免审**("我就不过目了,你自己能跟原始需求对上就行"),替代门 = agent 自核 R/V 对齐 V1.5 + 疑问先确认;② **specs 体系按指南落**:仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机;③ 质疑指南是否有大问题——对证结论:**三件事指南全有明文**(00-doc-map 阶段2 行 11–12、阶段3 行 13、02-dev-workflow §二),错在 agent 立结构时未查指南、自创 docs/specs/phase-N(lessons L9)。
- 现结构:specs/{INDEX.md, SPEC-template.md, spec-001(Phase 1 追溯建档,Done), spec-002(Ready)};docs/workflow.md 含本项目适配 A1–A5(一段=一个 Phase、免审门、界面确认以 V1.5 为基线、V1.5 兼任 spec/roadmap、R/V 指针化)。
- 给 owner 的建议(改不改他定):指南可补一小节"项目已有权威需求基线(如本项目 V1.5)时怎么接入 specs/ 体系"——本项目接法可直接参考 docs/workflow.md §五。
- **修改建议已成文**:[docs/AI-Project-Guide-revision-proposal.md](AI-Project-Guide-revision-proposal.md)(3 条建议:基线项目特殊入场、建新结构先对号的路由行、SPEC 文件名唯一格式;每条带插入锚点+可粘贴草稿+验证用例)——owner 将交给改指南的 agent 执行;指南改定后需重拷同步仓内快照(建议文末有命令)。
- spec-001 已应 owner 要求补全为完整 SPEC 形态(R10 条/V6 组/实现方案/测试矩阵/验收原话,2026-10-01);AGENTS 路由表同步加"建新结构先对号"一行(lessons L9 的结构性修法)。

### 2026-10-01 · Phase 1 放行;立"每 Phase 先写 Spec"规矩,Phase 2 Spec 待过目

> **下一步从哪接** —— owner 看 docs/specs/phase-2-file-system-and-favorites.md(重点 §四 实现决策 D1–D8)→ 无异议说"开工";有异议改决策表再开工。

- owner 原话"继续下一个阶段开发" = Phase 1 验收放行;同轮立新规矩:每段开发先写 Spec 文档再开发(建仓时"不另建 specs/"的取舍就此推翻,§二 已留痕)。
- Spec 只装实现方案+决策+测试验收,需求真值仍在 V1.5(防复述漂移);Phase 1 不追溯补写。
- Playwright 正式化挂账顺延(原定"Phase 1 验收时顺带定",owner 未提,仍挂账区)。

### 2026-10-01 · Phase 1 Application Shell 交付,等 owner 验收

> **下一步从哪接** —— owner 验收(testing.md §2 末尾有 2 分钟手测路径)→ 通过后进 Phase 2(V1.5 §176,一次只做一个 Phase)。

- ⚠️ 验收中发现并已修复两件(2026-10-01,release 已重建,细节在 testing.md §2"验收反馈修复"):① Remove 入口原来只在顶栏标签右键,现 Files 面板项目路径右键也有(共享组件 ProjectContextMenu);② 全局禁用了 WebView 默认右键菜单(此前会露出 Back/Reload/Print/Inspect)。owner 需用新 exe 重验。
- Python 一律用 conda pywork 环境(owner 指定,architecture.md §0)。
- Tauri 2.12 + Svelte 5(纯 Vite,剥掉模板 SvelteKit)+ single-instance + dialog 插件;工程结构见 architecture.md §3。
- 实测全过:单实例 / 项目标签增删切去重(含原生 Picker 全链自动化)/ Files·Git·Settings 壳 / Theme / Ctrl+R 物理级拦截(WebView2 加速键已 COM 禁用,Tauri 2 无配置项,lessons L5)。
- Baseline:启动冷 992ms·温 88ms;进程树 Private 179MB(⚠️超 150 target,判读见 testing.md §3,Rust 主进程仅 5.9MB);空闲 CPU 0.35% 单核;WebView2 6 进程。
- GUI 自动化测试基建(CDP+UIA,无需前台)方法在 testing.md §1、踩坑在 lessons L3/L4/L6–L8,下次做 UI 验证直接复用。
- 测试目录 `%USERPROFILE%\aiv-test-projects\`(Alpha/Beta 空目录)留给 owner 验收用,用后可删。

### 2026-10-01 · 会话收口:owner 确认建仓,批准开工

> **下一步从哪接** —— 新会话按 AGENTS.md 开机三步进来,直接执行 V1.5 §192(仅 Phase 1,完成即停等验收)。

- owner 拍板两件:① 初始化验收通过,批准进入 Phase 1 开发;② 异地备份不着急,V1 全部做完、owner 验收后再建(挂账已改期)。

### 2026-10-01 · Rust 工具链安装完毕,Phase 1 前提全部就绪

> **下一步从哪接** —— owner 确认后按 V1.5 §192 开始 Phase 1;开发环境已无阻塞项(备份 remote 仍是 owner 挂账)。

- rustup 用户级安装 rustc/cargo 1.98.1(msvc),VS 2022 Build Tools 已存在提供链接器,hello-world 编译运行验证通过。
- tauri-cli 决定用 pnpm 的 @tauri-apps/cli(JS 版,Phase 1 随脚手架安装),不装 cargo tauri-cli(免 10 分钟级本地编译)。

### 2026-10-01 · 建仓(按 AI-Project-Guide 阶段 0)

> **下一步从哪接** —— owner 确认建仓结果后,按 V1.5 §192 开始 Phase 1;先装 Rust 工具链,再输出工程结构与风险清单,只做 Phase 1。

- 需求经 V1.1→V1.5 五轮评审定稿,V1.5 FINAL 为唯一基线;旧版已删;
  V1.5 尾部 §196 为 ZCode 评审附注(附注 A 是 git 路径基准的事实性修正,Phase 7 前合入正文)。
- 本次建立:AGENTS.md / demand.txt / architecture.md(§0 环境已实测,D1–D9 决策已落表)/ 三份空账 / .gitignore / 首笔 commit。
- 环境实测:Node 24.14 + pnpm 11.1 ✅;**Rust 未安装** ❌(详见 architecture.md §0)。

## 二、为什么这么改(当批关键取舍;只在"后人容易被顺手的改法改回去"处留一句)

- **~~不另建 spec.md / roadmap.md / specs/~~**(2026-10-01 改口,出处:owner"每一段开发都要专门写一个 Spec 文档再开发";
  同日二次收紧:specs 按指南落仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机):
  现规矩 = **每个 Phase 开工前按 docs/workflow.md 状态机立 SPEC(根目录 `specs/spec-NNN`,编号与 Phase 对齐)**。
  spec-002 起执行,spec-001 追溯建档。原取舍(V1.5 兼任 spec/roadmap、待痛点出现再建)低估了"动代码前要有可审的实现方案与状态台账"这一痛点;
  V1.5 仍兼任产品规格与 roadmap(需求真值),specs/ 装实现方案与状态,两层用指针互指不抄正文。
- **需求变更走增量修订 + 变更审计(V1.5 §193),禁止整篇重写**:V1.2→V1.3→V1.4 三次整篇重写
  每次都丢过已确认规格,V1.5 起改为"只改明确条目+审计清单"后未再发生回归。

## 三、挂账区:等 owner 的事 + 非 SPEC 零散待办(一行一件,带去处)

> 债务表(debts.md)未建的阶段,这里就是**全部待办的家**;待办散落/约超 10 条 → 该建 debts.md。

| 事 | 去处(归谁·什么时候) | 提出日期 |
|---|---|---|
| 建异地备份 remote(私有库,SSH 认证),建好当天首推+核 0;建立之前仓库只有本地一份 | owner 亲手(方法:仓内 docs/AI-Project-Guide/07-backup-secrets.md)·**V1 全部完成后、owner 验收时**(2026-10-01 owner 拍板改期,不着急) | 2026-10-01 |
| V1.5 §196 附注 A(git -C 统一执行基准)合入 §65 正文 | agent·Phase 7 前 | 2026-10-01 |
| ~~**WebView2 划词阻塞:owner 选 A(升级 Runtime,推荐)/B(自实现选择层)**~~ 已闭环(2026-10-09 选 A,Runtime 143→155,实测全绿,见"现在在哪"首条;余 owner 复验) | owner 复验(重启 app 后划词)· ASAP | 2026-10-09 |
| ~~Playwright 回归脚本正式化入库~~ 已销账(2026-10-10 owner 点头,scripts/e2e/ 入库+testing.md §1.2/§1.3 正典化) | — | 2026-10-01 |
