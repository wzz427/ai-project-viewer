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

主线 = **spec-014 视觉改版 InTest**(owner 拍板 A 克制专业版/一步到位/亮色为主,布局不动;
范围=评审快照 P0–P2 全条目+transition;SPEC=specs/spec-014-visual-refresh.md)——施工完毕
(tokens 三档字阶/语义色/暗色三面阶梯+Icon.svelte 16 枚 SVG+首字徽标 hash 色身份+类型图标
与查看器路由同源+两级标签正交 40/28px),截图自检 7 张双主题过(2 处对比返修),全档回归
→ 发 0.7.14 → **等 owner 验收**。**T3 全过+0.7.12 冻结修复后,spec-011 验收仍等 owner 原话**
→ Done → NSIS 打包届时点头(webviewInstallMode 三选一)。
**版本段 0.7.x 固定递增不跳段**。
挂账两件见 §三(冻结现场验证 / 异地备份 remote)。
**冻结大案(2026-10-12 三次现场)**:修复已随 0.7.12 发(工作区 keyed+projectTabs 代理),
待 owner 现场验证;**若再冻结:别重启,说一声即上门**——dev/体验版常开 9322,
`pywork python scripts\e2e\live-inspect.py` 直读活体(项目/页签/DOM 三对照+日志环,L43);
应急恢复照旧:切 Git 面板点条目→切回 Files。
协作习惯:高频验收、编号反馈、返工轮是常态;测试零打扰红线(testing.md §1.2);e2e 一律 aivlaunch(PID 限定)+
**park_offscreen(L34)**。

## 一、现在在哪(最新在上)

### 2026-10-12 · 0.7.20:更新重启丢旗标修复(L48),黑线案真正收口

- owner『升级完还是不行,但副本没黑线』→零接触取证(psutil environ 双进程实读)定案:**更新器 relaunch 继承父进程 env,首写即赢闸门让新旗标每次更新重启后静默丢失**;修复=lib.rs env 补丁改幂等(缺啥补啥,端口按旗名查重),0.7.20 已发(UTF-16+旗标双核)。
- 全档:cargo 112+check 0/0+构建过;phase3 被 owner 试验副本(开发标识域)顶掉——环境性,前端与 0.7.19 全绿轮字节相同,**副本删除后补跑**。
- 下一步:owner Update→重启(此重启即实走幂等分支)→快速连点终验;确认后删试验副本。

### 2026-10-12 · 黑线案五轮:终判=呈现层伪影,试验副本已交 owner,🔴 别碰他的实例

- owner 两度给关键证据:拖窗自检(线跟窗走,推翻我'面板'误判)+**快速连点才触发**;快速连点复现时同窗口期 72 帧强制合成截图全零命中(owner 眼见线在)⇒铁证=线在应用像素之上、面板之下=DComp 呈现层。**owner 明令:不许再动他正在用的实例;方案一律走独立副本**。
- 试验修(单变量)=lib.rs 默认参数 `--disable-direct-composition`,构建 **0.7.19 试验副本**放 `Desktop\AIV-黑线试验版\`(dev 标识/独立存储/永不自动更新;cargo 112+check 0/0+phase3 PASS;正式渠道未发)。副本验证已过(owner 亲测黑线灭)→ **0.7.19 已发正式渠道**(UTF-16+旗标双核;等 owner Update+重启+快速连点终验;确认后可删试验副本——副本占开发标识域会顶掉 e2e)。
- 版本三处已到 0.7.19(未发布);0.7.14–0.7.18 验收仍等 owner。

### 2026-10-12 · 点击黑线三报结案:非软件(显示器面板伪影),L47

- owner 报'点项目页签必现黑线'+**截图拍不到/肉眼可见/数秒自消** ⇒ 直连逐层排查(进程/窗口/DOM/computed/根变量/CDP 真实输入点击+逐帧录屏)全零异常 ⇒ **面板伪影**(项目切换=大面积深字白底翻转,VA 拖影);给了 owner 拖窗自检法。**拖拽黑线=滚动条,已在 0.7.18 修复——两条黑线两个根因,别混**。
- 下一步:0.7.14–0.7.18 一并等 owner 验收。

### 2026-10-12 · 0.7.18 黑线修复+发布事故重发,等 owner Update+重启

- owner 报"拖动项目页签冒黑线(连拖必现,瞬态)"→探针复现定性=**横向滚动条滑块**(拖拽越缘触发
  overlay 滚动条浮现);修=html+两页签条 `scrollbar-width: none`(滚动功能保留)。
- **发布事故(L46)**:首轮发版漏 bump 版本→贴错标签的修复构建上架;owner 一次成功一次报错,
  之后按钮永灰、运行进程无修复(live-inspect 定案)。补=bump+重发真 0.7.18(UTF-16 核)+
  **publish 脚本加同版本拒发闸**。
- 下一步:owner 点 Update→**重启**(修复只在下次启动生效)→黑线验收;0.7.14–0.7.18 一并收口。

### 2026-10-12 · spec-015 项目页签拖拽换位 InTest:0.7.17 已发,等 owner 验收

- owner 增量需求"项目页签也能互相移动,吸取文件页签的教训"→**模型 1:1 复用**文件页签 L10 方案
  (双取消/半区/空带;拖拽≠切换;持久化=数组序零新字段);store 加 reorderProjects/moveProjectToEnd。
- recent-suite +6 守卫**一次全过**(21/21——复用打磨过的模型,零返修);指示线截图亲验;
  check 0/0+phase3 PASS+r3 8/8;0.7.17 发体验渠道(UTF-16 核)。
- 下一步:owner Update→验收原话落 spec-015 §六→Done;spec-014 视觉验收也等他(见上条)。

### 2026-10-12 · spec-014 视觉改版 InTest:0.7.15 返修已发,等 owner 验收

- owner 经双 Skill 评审(frontend-design+impeccable,19/40,快照 `.impeccable/critique/2026-10-12T09-25-27Z__src-app-svelte.md`)
  拍板 **A 克制专业/一步到位/亮色为主,布局不动** → 同日立 spec-014→施工→InTest→发版一条龙:
  三档字阶+语义色统一(--danger 唯一红/--accent-soft 染层/--accent-strong 实底)+暗色三面阶梯+
  **Icon.svelte 16 枚内联 SVG**(Unicode/emoji 清零)+项目**首字徽标 hash 色身份**+文件**类型图标族**
  (与查看器路由同源)+**两级标签正交**(项目条 40px 底条/文件条 28px 顶线)+100ms 过渡。
- 质量口:对比度 WCAG 全数值实测(SPEC §六账本),两处返修(亮面徽标字母压暗/Up-to-date chip 分主题);
  截图自检 7 张双主题(visual-check-014.py);全档绿 check 0/0+vitest **84**(+20)+phase3 70+git 33+
  recent 15+r3 8+pdf 23;e2e 断言按 **L44**(绑 data 属性不绑字形)同步三处。
- **0.7.15 返修**(owner 截图"×都看不到了"):0.7.14 曾给页签关闭钮加悬停才显形(非方案内)→恢复常显;
  check 0/0+phase3 PASS+r3 8/8+截图重验。同日**异地备份建线**(remote backup=GitHub SSH,规则住
  architecture §0;owner 确认项=库可见性 Private)。
- **0.7.16 二次返修**(owner 二报"啥回来了?你这是怎么验证的?"):live-inspect 直连实测=0.7.15
  修复确已生效但 × svg 只有 4×12px——真根因=按钮 UA 默认 padding 吃掉内容区(SVG 静默缩扁,文字
  时代无害)+长名截断挤压;修 padding:0+flex-shrink:0;**验证升级=visual-check 几何断言**(svg 盒
  ≥11px,两轮拦下坏构建);教训 **L45**(截图/视觉模型/像素桶全在 4px 细条上翻车,终审=几何断言)。
- 下一步:**owner Update 0.7.16 → 验收原话落 spec-014 §六 → Done**;spec-011 验收仍等他(§〇)。

### 2026-10-12 · 置顶星标改行尾图钉 0.7.13 已发(等 owner 点 Update)

- owner 截图报:置顶文件夹因名称前★占了子级缩进列,父子同名列层级不可辨;按其改法=标记移**行尾**+
  **图钉形状**(与页签置顶同语言 📌);可视化自检亲验层级立辨。
- 全档绿(check 0/0+vitest 64+phase3 70+r3 8+pdf 23);0.7.13 已发体验渠道。

### 2026-10-12 · 冻结大案定位+修复 0.7.12+活体直连通道(等 owner Update+现场验证)

- 现场#3 的 MISMATCH 行实锤断链层(仅 viewer 派生死);本地 96 轮仅 1 中(≈2%,A/B 不可行)
  →机理修复:**App 工作区按 rootPath keyed**(切项目=干净重挂,订阅不跨重定向变陈旧)
  +projectTabs() 创建路径回读代理;全档绿(cargo 112+phase3 70+git 33+recent 15+r3 8+pdf 23
  +vitest 64+check 0/0+probe 6/6),0.7.12 已发体验渠道。
- **活体直连**(owner"直接获取我本地软件里的信息"):dev/体验版常开 CDP 9322
  +window.__aiv.snapshot() 只读探针+live-inspect.py(绝不 launch/kill/focus);实测附身运行中
  实例全量吐出 ✓;生产打包须关端口(spec-011 NSIS 步记账)。
- 下一步:owner Update→日常用;再冻结**别重启,喊我上门**;spec-011 验收仍等 owner。

### 2026-10-12 · 冻结大案二次现场+取证升级 0.7.11 已发(等 owner 点 Update)

- owner 现场报"切任何页签内容不变"+导诊断:**铁证**=14:09:50–53 三次快速项目切换后,四次页签
  操作零 viewer 事件(store/页签条活性正常,live-check 双证一致;环零报错=信号图级静默失联,
  非异常);本地两版 42 轮(快速切换/嵌套项目根/盘上搅动)未复现——按纪律不动行为代码,装取证。
- 0.7.11(取证向):viewer `data-rel` 标记+诊断导出 **MISMATCH 行**+console.error/warn 入环(去重)
  +四条盲路径补记(cycle/neighbor/re-open/add);phase3 +2 **内容身份守卫**(70/70——此前所有
  套件只查页签名+类名,从不查内容身份,这正是三轮复刻全绿而 owner 客户端冻结的原因);
  r3 8/8+pdf 23/23+vitest 64+check 0/0;已发体验渠道(UTF-16 核)。
- 下一步:owner 点 Update 装上取证版;**再现即导出**(新导出自带 mismatch 行)→根因→修复;
  T3 已全过,spec-011 验收仍等 owner;应急恢复配方见 §〇。

### 2026-10-12 · T3 全量基准跑完(A–I+Baseline 全过),等 owner 验收 spec-011

- owner"开跑"(红线授权)→ 新建 scripts/e2e/benchmark-suite.py(A–I+Baseline 合一,九档全跑门全过,
  私有字节全进程树口径)。关键数:前端就绪 ≤1.2s/空闲 CPU 0.12 CPU·s/min/空闲 RAM 200.2(150 target ⚠ 非 gate)/
  10 页签 +25MB/4 项目恢复 685ms/10.5 万文件零递归扫描/Agent 锤击防抖 3.5:1/PDF 5 页签 1.6×/25k 行 diff 截断 182ms/
  git-suite 33/33。全文=testing.md §4 T3 行。
- 附带两判:①PDF 反复开关 5 轮+强制 GC 探针=渲染进程平台化、GPU 光栅缓存非单调 ⇒ **无应用侧无界泄漏**
  (Phase 5 单轮"无泄漏"弱判断升级为有界判读);②基建发现 **L42**(window_of 停错窗)。
- 下一步:owner 验收原话落 spec-011 §六 → Done → NSIS(webviewInstallMode 三选一点头)。

### 2026-10-12 · spec-013 验收 Done(0.7.10),主线=T3 全量基准待 owner 点头

- owner 验收原话"过了。进入下一个需求"落 SPEC §六,spec-013 Done(遗留零,开关常开)。
- 下一步 = T3 全量性能基准(A–I 档+Phase 1 Baseline,数小时):**红线=开跑前 owner 批**;
  已向他说明 T3 内容,等点头。跑完 → spec-011 复验 → Done → NSIS 打包三选一点头。
- 挂账不变:冻结 bug 取证(§〇)/异地备份 remote。

### 2026-10-12 · spec-013 前端加固批 0.7.10 已发,等 owner 验收(已验收,留档)

- owner"发版没那么急,先做这个需求,清掉这个问题"(=清 spec-012 D12 记档的 60 处,T3 顺延)
  → spec-013 立项开工;60 处清零(产线 22 守卫/结构改写+测试 38 断言,归型清单 SPEC §六),
  **noUncheckedIndexedAccess 常开**——此后新代码同类隐患编译期拦截。
- 全档全绿:check 0/0+vitest 64+phase3 68+git 33+recent 15+r3 8+pdf 23;cargo/watcher 零改动免跑;
  0.7.10 体验渠道已发(VERSIONINFO 核过)。
- 挂账不变:冻结 bug 取证(§〇)/异地备份 remote。

### 2026-10-12 · spec-012 验收 Done,主线交棒 T3 全量基准

- owner 原话"spec012可以done"落 spec-012 §六(InTest→Done 硬门过);INDEX 同步两行
  (spec-012→Done 冷却待搬;spec-011 去处切"下一动作=T3,开跑前按红线再确认");
  评审报告 git mv → history/code-reviews/(INDEX 快照轴登记;断链修指四处:spec-012 头引/INDEX
  两行/progress 时间轴)。
- 下一步 = **T3 全量基准:开跑前找 owner 再确认一次**(红线"全量测试批准";预告授权留痕在
  INDEX spec-011 行)→ 跑完 spec-011 复验 → NSIS 打包届时点头(webviewInstallMode 三选一)。
- 遗留仅 L-c6 记档:tsconfig noUncheckedIndexedAccess 实测 60 处/8 文件,超 D6 止损线 20 未在本批清,
  去处=下一前端专项批次(2026-10-12 owner 问询过是什么,已在对话中解释)。

### 2026-10-12 · 本段收口:code review→修复批 0.7.8→高亮返修 0.7.9,主线交棒新对话

> **新会话从这接** —— 读 AGENTS.md 开机三步 → 本页 → specs/spec-012-code-review-fixes.md(§六)+lessons L41。
> 本段全程:全面 code review(报告 44 条)→ owner"开工,完成spec012" → 43 条一批修完(42 落地+L-c6 止损)
> → 全档回归全绿 → 0.7.8 发体验渠道 → InTest 报障(右键动作后树高亮)当日返修 0.7.9 再发。
> 全程蒸馏在 history/progress/progress-2026-10.md(Grep spec-012/0.7.8/0.7.9/L41)。

- 交接要点:①体验渠道当前版 **0.7.9**,spec-012 验收已过(见上条)——评审报告已归
  history/code-reviews/ 快照轴;②T3 全量基准=V1.5 §162–§173+testing.md
  §4.9 口径,owner 已预告授权(原话留痕在前段收口条,蒸馏件可 Grep "T3 排期授权");③NSIS 打包须届时点头
  (webviewInstallMode 三选一,spec-012 D7);④新报障第一动作=Settings→Export Diagnostics 同机直读;
  ⑤动 watcher 链发版前必跑 freeze-guard;⑥tsconfig 收紧记档待清(60 处,去处=下一前端专项批次)。
- 挂账不变:冻结 bug(取证路径见 §〇)/异地备份 remote(V1 验收后 owner 亲手)。
- ⚠️ docs/AI-Project-Guide/ 的未提交改动归另一会话,勿动勿提交勿还原。

## 二、为什么这么改(当批关键取舍;只在"后人容易被顺手的改法改回去"处留一句)

- **~~不另建 spec.md / roadmap.md / specs/~~**(2026-10-01 改口,出处:owner"每一段开发都要专门写一个 Spec 文档再开发";
  同日二次收紧:specs 按指南落仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机):
  现规矩 = **每个 Phase 开工前按 docs/workflow.md 状态机立 SPEC(根目录 `specs/spec-NNN`,编号与 Phase 对齐)**。
  spec-002 起执行,spec-001 追溯建档。原取舍(V1.5 兼任 spec/roadmap、待痛点出现再建)低估了"动代码前要有可审的实现方案与状态台账"这一痛点;
  V1.5 仍兼任产品规格与 roadmap(需求真值),specs/ 装实现方案与状态,两层用指针互指不抄正文。
- **需求变更走增量修订 + 变更审计(V1.5 §193),禁止整篇重写**:V1.2→V1.3→V1.4 三次整篇重写
  每次都丢过已确认规格,V1.5 起改为"只改明确条目+审计清单"后未再发生回归。
- **版本段 0.7.x(2026-10-11 起)**:owner 明令"版本升到0.7"——D7 规则(0.6.x 固定递增不跳段)的逃逸条款
  "直到 owner 另有指令"首次使用;递增纪律不变,只是换段。

## 三、挂账区:等 owner 的事 + 非 SPEC 零散待办(一行一件,带去处)

> 债务表(debts.md)未建的阶段,这里就是**全部待办的家**;待办散落/约超 10 条 → 该建 debts.md。

| 事 | 去处(归谁·什么时候) | 提出日期 |
|---|---|---|
| ~~建异地备份 remote~~ | **已建线清偿(2026-10-12 owner 委托指令)**:remote `backup`=GitHub SSH,首推 main 核 0;规则八条住 architecture §0「备份规则」;遗留 owner 确认项=网页上看一眼库是 **Private** | 2026-10-01(2026-10-12 清) |
| **内容区冻结 bug**:owner 客户端切任何页签,页签条/树高亮都变但主区内容停在旧文件(2026-10-11 报障,三次现场) | **修复已随 0.7.12 发**(D12 工作区 keyed),待 owner 日常使用现场验证;若再现:别重启,live-inspect 直连 9322(见 §〇) | 2026-10-11 |
