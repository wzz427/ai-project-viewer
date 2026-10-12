# SPEC-014-视觉改版:布局不动、只换"皮"——两级标签一眼分清、图标成体系、颜色有语义

> 创建:2026-10-12。Pre-Draft 结论出处:impeccable 双代理评审(快照 `.impeccable/critique/2026-10-12T09-25-27Z__src-app-svelte.md`,
> 19/40)+ frontend-design 方案 A/B 对照 → owner 经 AskUserQuestion 拍板:**方案 A 克制专业版 / 一步到位(不分批)/ 亮色为主**。
> A2 说人话对齐已随评审+拍板完成(workflow §五免重复对齐),本页 §一/§二 即对齐产物。

## 〇、值不值得做(两栏三出口,一行各一句)

- 好处:owner 自己每天用的高频界面;评审 19/40(Poor 边缘)——项目/文件标签同形是他原话点名的"容易搞混",图标是 Unicode/emoji 拼凑,全员受益。
- 代价:纯前端一批(app.css tokens+Icon 组件+约 15 个组件的 style 块);可能碰坏=e2e 选择器(×/⚙/📌 等字形改 SVG)、暗色可读性回归、tab 几何变化碰 drop 线断言。
- 判:值→做(owner 已拍板"我确认后再改"→三问答确认)。

## 一、Pre-Draft 结论(讨论过了才许写这份文档)

- 核心选择题:A 克制专业版(单 accent、灰阶纪律、VS Code 式安静)vs B 个性版(项目色身份贯穿、更强表达)——owner 拍 **A**;分批 vs 一步到位——拍**一步到位**;主题侧重——拍**亮色为主**(暗色同步修阶梯,不另起炉灶)。
- 标杆对照:VS Code/Linear 式安静工具;与 B 的差别=不加装饰性渐变/大色块,层级靠**正交词汇**不靠响度。
- **界面确认**:评审报告(P0–P2 清单+两级标签方案)+ 三问答,owner 2026-10-12 点头;"布局不要改"是他原话红线——见 R0 反例规则。

## 二、需求正文(R 编号;使用者视角)

| R# | 需求(使用者视角) |
|---|---|
| R0 | **(红线)**界面结构零变化:侧栏位置/宽度行为、树行高、查看器区域划分、无新增/删除条带都不变;唯一允许的尺寸变化=owner 拍板方案里点名的项目条 36→40px、文件标签条 32→28px |
| R1 | 打开多个项目,项目条与文件标签条**一眼分属两层**:项目条=chrome 带(40px,底部粗 accent 线,每项目带首字徽标,徽标颜色由项目路径决定、跨会话稳定);文件标签=浏览器式细条(28px,顶部细 accent 线) |
| R2 | 同一项目在任何时候徽标同色;不同项目大概率不同色(色板循环) |
| R3 | 界面所有图标来自一套 16px/1.5px 描边单色 SVG(随文字色),替换现有 Unicode/emoji(📌⚙↻✕×▸⎇›‹⬆);Git 徽标 `[7]` 变为 accent 色计数 pill |
| R4 | 文件标签带**类型小图标**(md/pdf/代码/json/图片/其他 六族,与实际打开的查看器路由同源),当前树里的文件行"横点"换成文件图标(槽位尺寸不变) |
| R5 | 选中/激活态在灰阶之上有 accent 染色层:树选中行、侧栏活动页签、项目活动标签都能"一眼定位于哪个" |
| R6 | 正文字阶三档(11/12/13px),不再有 10/10.5/11.5/12.5/14/15/16px 散布;层级靠字重(600)与颜色,不靠多档字号 |
| R7 | 次要文字(muted)在两种主题的常用底色上对比 ≥4.5:1;危险/错误色全应用一个 `--danger` 语义令牌(现在 4 种红并存),git 状态色独立成族不受影响 |
| R8 | 暗色主题壳/阅读面/浮层三面拉开(现三面差 <3%):阅读面最亮作舞台,浮层(菜单/弹窗/toast)最亮于壳且带阴影 |
| R9 | 交互态(hover/active/页签/按钮/树行)有 ~100ms 过渡;现有刷新旋转动画保留 |
| R10 | 亮色为主:亮色主题的灰阶/对比同样按 R5–R8 纪律重调,不是只改暗色 |

**反例规则(不许做什么)**:R0 不许动任何组件的结构/DOM 层级/交互行为(纯视觉层:CSS/字形/图标);不许引入新依赖(图标=手写内联 SVG 组件);不许引入动画库或 >150ms 的动效;不许改 Rust 侧任何东西;`aria-label`/`title`/role 等 e2e 与 a11y 依赖的属性值保持不变。

## 三、验证标准(V 编号;可判定,直接变测试用例)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1 | 截图(亮+暗):项目条高 40px、活动项目有底部 accent 线+首字徽标;文件标签条高 28px、活动页签顶部 accent 线;两条视觉形态明显不同(正交:粗底线 vs 细顶线、徽标 vs 类型图标) | 人工(V-human) |
| V2 | R2 | 同一 rootPath 两次启动徽标同色;avatarColor 纯函数直测(确定性+色板内) | 自动(vitest) |
| V3 | R3 | `grep` 全 src 无 📌/⚙/✕/⎇/⬆ 等字形残留(注释除外);Git 徽标为 pill 元素非 `[7]` 文本 | 自动(脚本 grep)+人工 |
| V4 | R4 | 文件标签与树文件行的图标族与 viewerType 路由一致(md 打开 Markdown 查看器→文档图标);六族映射直测 | 自动(vitest)+人工 |
| V5 | R5/R7 | 对比度计算脚本:muted×{bg,bg-hover,viewer-bg}、danger×{bg,viewer-bg} 两主题全部 ≥4.5:1,数值落 SPEC §六 | 自动(Python 计算记录) |
| V6 | R6 | `grep` 组件 style 无 10/10.5/11.5/12.5/14/15/16px font-size 残留(除 --viewer-font-size 用户旋钮与查看器内容区) | 自动(grep) |
| V7 | R8 | 截图(暗):壳/阅读面/浮层三面亮度目测可分;token 值差 ≥3% | 人工+自动(token 记录) |
| V8 | R9 | 页签/树行 hover 有 ≤150ms 颜色过渡(CSS 检视) | 人工 |
| V9 | R0 | 五套 e2e(phase3/git/recent/r3/pdf)全绿=行为与选择器未破;check+vitest 绿;cargo 未动 Rust 免跑 | 自动 |
| V10 | 全局 | 截图自检无元素溢出/截断/重叠;主题切换(亮↔暗)后无残留旧 token | 人工(V-human) |

人工项 4(V1/V7/V8/V10),自动 6,满足"人工 ≤ 自动一半"边缘(4 vs 6)——V8 并入 V1 截图检视执行,实际三张截图覆盖。

## 四、技术实现方案(三步曲 (b):确认后才开发)

- 模块拆分:
  1. `src/app.css` —— tokens 重构:字阶(--text-xs/sm/base)、语义色(--danger、--accent-soft 染色层、--bg-overlay)、两主题灰阶/暗色三面阶梯、--radius-pill、--transition-fast;
  2. `src/lib/components/Icon.svelte`(新)—— 16px/1.5px/currentColor 内联 SVG 集(plus/x/gear/refresh/chevron-right/chevron-left/pin/git-branch/check/circle-fill/arrow-up/file/file-text/file-code/braces/image ≈16 枚);
  3. `src/lib/services/avatarColor.ts`(新,纯函数)+vitest——rootPath hash→8 色板(两主题同板,饱和度低的专业色);
  4. `viewerType.ts` 加 `iconFamilyOf(rel)` 纯函数(路由同源)+vitest;
  5. 组件 style 批改:ProjectTabs(40px chrome+徽标+底 accent 线)/FileTabs(28px+顶线+类型图标)/SidebarHeader(pill 徽标+SVG)/TreeItem(chevron+file SVG 进既有 12px 槽)/GitPanel(⎇›→SVG,字阶)/App/App.css 尺寸归一/UpdateButton/Toast/菜单浮层(--bg-overlay)。
- 关键取舍:图标手写内联(否决 iconify/库依赖——内存最小化+离线);字阶三档(否决五档——评审指半像素档是噪声);徽标色 hash 稳定(否决随机/session 态——R2);active 染色用半透明 accent 层(否决实色——quiet 基调+两主题一次算对)。

### 决策依据(后续翻案只翻这节)

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 | 图标=手写内联 SVG 单组件 | 零依赖零网络零字体文件;16 枚可控 | iconify/lucide 包 | 新依赖+运行时解析;内存最小化红线 |
| D2 | 字阶 11/12/13 + 600 字重 | 评审 P1:七档半像素无层级信号 | 五档字阶 | 层级靠字重/颜色已够,档多是噪声 |
| D3 | 项目徽标色=hash(rootPath)→固定 8 色板 | 跨会话稳定=颜色身份可学习;8 色低饱和专业板 | 随机色/session 内序号 | 不稳定则颜色身份不成立 |
| D4 | 文件标签图标族复用 viewerType 路由 | 图标=「会打开什么」的真实预告,两套分类必漂 | 独立图标分类表 | 双真值漂移 |
| D5 | active 染色层=accent 半透明 | 两主题一个 token 拍定;quiet 基调 | 实色填充 | 响度超 A 方案;暗色易脏 |
| D6 | 暗色三面:壳最暗/阅读面中/浮层最亮+阴影 | 阅读面是舞台(评审解锁题②);浮层靠亮度+阴影双 cue | 壳亮于内容 | 削舞台;Electron 默认感来源 |
| D7 | `--danger` 两主题各一值(对比达标),git 色族独立 | 语义动作色 vs 状态色是两族;4 红并存根因=缺令牌 | 全并成一红 | git-d 是数据着色,拉低会失去族区分 |
| D8 | 项目条 40/文件条 28 | owner 拍板方案原文(正交词汇的一部分) | 全部保持原高 | 36/32 差 4px 无层级信号 |

**同一条依据已同步写进它管的那段代码的头注释**(依据和它管的东西不许分家):D1→Icon.svelte 头注,D3→avatarColor.ts 头注,D4→viewerType.ts iconFamilyOf 头注,tokens 依据→app.css 头注。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1/R5/R8/R9 | V1/V7/V8/V10 | 截图自检(亮+暗,本 repo 4 项目夹具)+token 检视 | 体验夹具仓 | ⚠(施工后跑) |
| R2 | V2 | vitest 直测 avatarColor | 无 | ✓ |
| R3 | V3 | grep 字形残留脚本 | 无 | ✓ |
| R4 | V4 | vitest 直测 iconFamilyOf | 无 | ✓ |
| R6 | V6 | grep font-size 残留 | 无 | ✓ |
| R7 | V5 | Python WCAG 对比计算,数值记 §六 | 无 | ✓ |
| R0 | V9 | 五套 e2e+check+vitest | 既有 make-fixtures | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物(矩阵/自检/验收原话) |
|---|---|---|
| 2026-10-12 | 创建(Ready→InDev 同日:范围=评审快照 P0–P2 全条目+transition,owner 已拍) | 本页;INDEX 行 |
| 2026-10-12 | InDev 施工完毕→InTest(截图自检 7 张过,2 处对比返修) | 见下账本 |
| 2026-10-12 | 全档回归绿→**0.7.14 发体验渠道**(UTF-16 核 0.7.14 无 0.7.13 残留);e2e 断言 L44 同步 3 处(git 徽章/指示器 data-state/recent .tab-name) | INDEX→InTest;testing.md §4 0.7.14 行;等 owner 验收 |
| 2026-10-12 | InTest 报障返修 **0.7.15**(owner 截图"×都看不到了"):0.7.14 曾给页签关闭钮加悬停才显形——非方案内、自作主张,恢复常显(muted/悬停提亮);check 0/0+phase3 PASS+r3 8/8+截图重验 4 页签 × 全显;已发体验渠道 | testing.md §4 0.7.15 行 |
| 2026-10-12 | 二次返修 **0.7.16**(owner 二报"啥回来了?"):live-inspect 直连实测 × svg 仅 4×12px——真根因=按钮 UA 默认 padding 吃掉内容区(SVG 静默缩扁)+长名截断挤压;修 padding:0+flex-shrink:0;**验证升级=visual-check 几何断言**(量 svg 盒 ≥11px,坏构建两轮当场拦下);0.7.15 的"截图重验"作废重记(教训 L45);已发体验渠道 | testing.md §4 0.7.16 行;lessons L45 |

### InTest 自检账本(2026-10-12)

- **V2/V4 自动**:`pnpm vitest` 84 全绿(新增 avatarColor 5 + iconFamily 15);`pnpm check` 0/0。
- **V3 守卫**:grep 全 src 无 📌/⚙/✕/⎇/⬆/▸ 字形残留(代码行,注释与 Icon.svelte 对照表除外);Git 徽标=[N] 文本已改 accent pill(e2e 断言同步:git-suite 徽章 "7"、指示器改读 data-state)。
- **V6 守卫**:组件 style 无裸 px 字号残留;唯一白名单=EmptyState h1 20px(文件内注释文档化的 hero 例外);字阶 token=11/12/13。
- **V5 对比度(WCAG,脚本实测)**:
  - muted 亮 #5d6470:bg 5.32 / hover 4.95 / active 4.54 / viewer 5.96 / raised 5.66
  - muted 暗 #989eab:bg 6.61 / raised 6.15 / hover 5.50 / active 4.93 / viewer 5.86 / overlay 5.36
  - danger 亮 #cf222e:bg 4.78 / viewer 5.36;danger 暗 #f0635a:bg 5.62 / viewer 4.98 / overlay 4.55
  - accent 亮 #2f6db3 白字 5.30;accent 暗 #5c96d0:bg 5.69 / viewer 5.04;实底按钮改用 --accent-strong(#2f6db3,白字 5.30)
  - 头像字母(身份徽标,≥3:1 图形口径):暗=全色相 3.08–3.99;亮=全色相 72% 混墨后 4.09–5.20(返修①:全饱和字母曾低到 2.73)
  - "Up to date" chip(返修②):0.6 透明度实测暗 3.4 → 改为仅暗色主题 0.8(4.68),亮色全不透明靠 muted+发丝边框压存在感
  - 暗色三面阶梯(相对亮度):壳 #16181c 0.0091 / 侧栏 #1c1f24 0.0135 / 阅读面 #202329 0.0167 / 浮层 #262a31 0.0229——阅读面较壳 +84%,浮层较侧栏 +69%(改前三面差 <3%)
- **V1/V7/V8/V10 人工(截图 7 张,%TEMP%\aiv-014-shots,双主题)**:两级标签正交成立(40px 底条+徽标 vs 28px 顶线+类型图标);类型图标 6 族与查看器路由同源;选中行=accent 染色层+左缘 2px 线;Git 面板分支图标/计数 pill/状态字母两主题全可读;右键菜单=浮层(亮面+阴影+边框);暗色三面阶梯目测可分;无溢出/截断/重叠;主题切换无残留。像素抽样核验徽标=15% 染底+彩字(视觉模型误读为实底,像素值 (206,207,232) 证实染层)。
- **V9**:交互态统一 `var(--transition-fast)`=100ms 颜色过渡(页签/树行/按钮/菜单项);`prefers-reduced-motion` 全局降级;刷新旋转动画保留(spin 测试仍走 .glyph)。
