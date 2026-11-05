# SPEC-018-链接跳转定位(标题用 owner 会问的那句话:点了文档里的链接,树里怎么找不到它?复制的绝对路径怎么带着 `docs\..`?)

> 状态唯一真值 = INDEX.md;实施记录见 §五。创建:2026-11-05;owner 报障两条(带双截图,
> QuantTrading 项目实案)。**2026-11-05 owner 三点全确认**(主修复/B 部分随做/`/` 根相对,
> 原话「三个点都同意,开始做吧」)后开工——D2 由"默认待确认"转正。

## 〇、值不值得做(两栏三出口,一行各一句)

- 好处:凡是用 Markdown 内链跳转的场景(AGENTS/SKILL/文档交叉引用,owner 日常高频)每次点击都中招;复制出的路径含 `docs\..` 脏段,贴进终端/工具有概率失效——用户可感觉的 bug,不修不合规矩。
- 代价:小——一个纯函数 + 两处调用点替换 + 树可见性过滤加一个可选参数;可能碰坏:图片 src 解析走同一函数(一并覆盖,回归靠单测+守卫)。
- 判:值→做。

## 一、Pre-Draft 结论(报障原文归纳 + 一个事实澄清)

- **owner 报障①**:点文档内链接跳转后,左侧树不定位目标文档;他观察到"开关显示隐藏打开也一样不定位"。
- **owner 报障②**:右键复制绝对路径 = `...QuantTrading\docs\..\.agents\skills\agent-team-workflow\SKILL.md`,真实路径无 `docs\..\` 段。
- **owner 拍板(原则)**:「在查看这种隐藏文件夹下的文档期间,该文档、文件夹及其父文件夹,都应该临时显示在左侧的文件树中。当该文档关闭时,如果设置里依然未开启显示隐藏开关,届时文件夹再自动消失」。
- **事实澄清(必须先对齐)**:本案的 `.agents` **并不在默认隐藏表里**(Rust `DEFAULT_HIDDEN_DIRS` 仅 8 名:.git/node_modules/.venv/venv/__pycache__/.cache/.next/coverage),开关关着它也一直在树里。①②两条症状的真凶是**同一个**:链接拼接出的相对路径没做规范化(`docs` + `../.agents/...` → `docs/../.agents/...`),脏路径既让树按段展开时撞上不存在的 `..` 节点(开关两态都定位失败),又被「复制绝对路径」原样拼出去。owner 的「临时显示」原则在本案其实不触发,但对真隐藏目录(如链接指向 node_modules 内的 README)依然成立——本 SPEC 把它作为 B 部分独立落地(A 部分单独即可修完 owner 报的两条)。
- 界面确认:无新界面;B 部分是树的视觉行为,交付前按铁律走视觉模型亲验。

## 二、需求正文(R 编号;使用者视角)

| R# | 需求(使用者视角) |
|---|---|
| R1 | 在 Markdown 里点击指向项目内另一文件的链接:右侧打开目标,**左侧树同时展开并滚动定位到该文件行**(「显示系统/生成文件夹」开关无论开关) |
| R2 | 对经链接打开的文件右键「复制绝对路径」:得到与资源管理器一致的干净绝对路径(无 `..`/`./`/双斜杠段) |
| R3 | 同一文件无论从树点开还是从链接点开,页签只有一个(现状:脏路径键不匹配会开两个) |
| R4 | (B 部分,owner 原话语义)经链接打开位于**真隐藏目录**(8 名单内)下的文件期间:该文件行及其全部隐藏祖先目录行临时显示在树中;当该文件最后一个页签关闭且开关仍关,这些行自动消失。开关开着时一切照旧 |
| R5 | (随行)Markdown 图片 src 同样按规范化路径解析(`../img/`、`%20` 空格、`./` 前缀不再丢图) |

**反例规则(不许做什么)**:不替用户翻转「显示系统/生成文件夹」开关(临时显示是派生呈现,不动设置持久值);开关关闭时不在树的常驻列表里永久露出隐藏目录;链接逃出项目根时不尝试打开、不清自动跳浏览器,报一条明确 toast 即止。

## 三、验证标准(V 编号;可判定,直接变测试用例)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1 | vitest:`resolveDocLink("docs/a.md","../.agents/s/x.md")` = `.agents/s/x.md`;`./b.md`、`docs//c.md`、`%20`、`#锚点`、`?查询`、逃逸根(→null)全形态过 | 自动 |
| V2 | R1 | phase3 守卫:夹具 md 含 `../` 链接,点击后 `.row[title="<规范化rel>"]` 存在且树已展开祖先链 | 自动 |
| V3 | R2 | phase3 守卫(复用既有 copy 守卫形态):对链接打开的文件走「复制绝对路径」,剪贴板串不含 `..` 且与拼 `root\<规范rel>` 相等 | 自动 |
| V4 | R3 | vitest/守卫:先链接打开再树点同一文件,`openFiles` 中该文件页签数 = 1 | 自动 |
| V5 | R4 | vitest(treeSort):`keepNames` 命中时 systemGenerated 目录行进入可见列表;phase3:开 node_modules 下文件→行可见,关闭页签→行消失 | 自动 |
| V6 | R4 | 视觉模型亲验:开关关、临时链显示中的树截图(两主题),隐藏祖先行渲染正常且置灰样式在 | 人工 |
| V7 | R5 | vitest:图片 src `../img/a%20b.png` 解析为规范化 rel | 自动 |

## 四、技术实现方案(三步曲 (b):确认后才开发)

- **模块拆分 / 动哪些文件**:
  1. 新 `src/lib/services/mdLinks.ts`(纯函数,零依赖):`resolveDocLink(docRel, href): string | null`——percent 解码(markdown-it 会把空格编成 `%20`,`%` 本身编成 `%25`,round-trip 安全)、剥 `#锚点`/`?查询`、按 `/` 切段、对文档所在目录消解 `.`/`..`、拼回规范 `/` 路径;逃逸项目根返回 null。
  2. `MarkdownViewer.svelte` 两处替换:链接点击(:81)与图片 src(:52)`joinRel(dir, …)` → `resolveDocLink(tab.relativePath, …)`;null(逃逸)走既有 toast 错误路径。
  3. `treeVisibility.ts`/`treeSort.ts`:`visibleEntries` 加可选 `keepNames: Set<string>`(该层须保留的目录名——systemGenerated 但被打开中文件祖先命中);`visibleSorted` 透传。
  4. `FileTree.svelte`/`TreeItem.svelte`:各加一个 `$derived`——由 `tabsStore` 该项目 `openFiles` 派生隐藏祖先目录名集合(纯 `ancestorDirsOf(rel)` 帮助函数放 treeSort),传入 3。组件层本就同时依赖两 store,无循环依赖;fileTreeStore 不反向 import tabsStore。
  5. Rust **零改动**。
- **关键取舍**:在**拼接点**(MarkdownViewer)修而不是在 `openFile` 里兜底规范化——其余 4 个 openFile 调用方(树/Git 面板/右键菜单/按路径定位)产出的都是规范路径,公共入口兜底会把「上游约定」糊掉,补丁式;B 部分用**派生**(每次渲染从 openFiles 现算)而不是维护一份持久 force-show 集合——不新增驻留、无陈旧态可漂,关页签即消失天然成立(内存最小化第一原则)。
- **内存账**:A 部分新增纯函数零驻留;B 部分每渲染 O(打开页签数×路径深度) 的派生 Set,不持久化。

### 决策依据(后续翻案只翻这节)

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 脏路径在 MarkdownViewer 拼接点修 | 唯一脏源在此;其余调用方均规范 | openFile 入口统一规范化 | 公共入口兜底=补丁式,糊掉上游约定 |
| D2 链接以 `/` 开头按**项目根相对**解读 | 对齐 VS Code;markdown-it 原样透传 `//` 会在 joinRel 产出双斜杠脏路径 | 按字面拼进当前目录 | 与业界语义相悖,且产出新脏形态。**默认待 owner 确认** |
| D3 逃逸项目根 → toast 不打开 | Rust `resolve_inside` 本就拒绝逃逸;前端提前判掉让报错可读 | 静默忽略 | 用户点了没反应属静默失效 |
| D4 临时显示集合 = **全部打开页签**的隐藏祖先(非仅活动页签) | owner 语义「该文档关闭时再消失」——多页签同链时以最后一个关为准;派生自 openFiles 天然成立 | 仅活动页签的链 | 切走页签树行闪烁消失,违背「查看期间显示」 |
| D5 根层「+N 系统文件夹」计数提示不动 | 它描述的是开关状态,非当前可见集合;减一反而引入两处真值 | 临时显示时计数-1 | 一份计数一个含义,不并列第二口径 |
| D6 存量脏页签(本次修复前经链接打开、已入会话)不做迁移 | 关掉即自愈;迁移逻辑一次性收益不值其复杂度 | 会话恢复时规范化重写 | 为历史脏数据加代码路径,边际负 |

**同一条依据已同步写进它管的那段代码的头注释**(依据和它管的东西不许分家)——开工时随代码落。

## 五、Ready(停工线)→ 已过

方案落纸面完毕后停工等确认;2026-11-05 owner 原话「三个点都同意,开始做吧」——D2 转正,B 部分随做,版本 0.8.19。**验收路径**(owner 复现报障即可):在 QuantTrading 里打开 docs/ 下那篇文档,点指向 `.agents/skills/agent-team-workflow/SKILL.md` 的链接——右侧打开、左侧树展开定位到该文件行;右键该页签「复制绝对路径」= 干净路径;再点一个指向 node_modules 内文件的链接(若项目里有),树里临时亮出整条隐藏链,关掉该页签链即消失。

## 六、实施记录(2026-11-05,0.8.19)

- **代码**:新 `src/lib/services/mdLinks.ts`(纯函数 resolveDocLink:剥锚点/查询、percent 解码、`/`与`\`双分隔、`.`/`..` 消解、`/` 根相对、逃逸根→null);MarkdownViewer 链接/图片两处换用;`treeVisibility.ts` 加 keepNames/openChainDirs/keepNamesUnder,`treeSort.ts` 透传;FileTree/TreeItem 各一条 $derived 由 tabsStore.openRelsOf 派生隐藏祖先链;i18n 新键 toast.linkOutsideProject(en/zh);Rust 零改动;**零新增驻留**(链集合为每渲染派生、不持久)。
- **测试**:vitest +28(mdLinks 23 全形态/treeVisibility 5)→149/149;cargo 132/132;phase3 **PASS×2 连跑**(129 守卫,+7 spec-018:md_link_reveals_in_tree/tab_dedup/copy_abs_clean/percent20_opens/anchor_stripped/hidden_chain_shows/hidden_chain_hides_on_close);夹具 +docs/guide.md+docs/my file.md(主)+ away 侧 node_modules/dep 种子。
- **视觉亲验**(铁律 §2.3-6):一次性探针三截图(临时显示链 paper/glacier 双主题+关闭后消失),视觉模型逐张判读全过——链可见且展开、目标行选中态、无截断重叠;「+1 system folder hidden」计数提示保留(D5 预期,描述开关状态不减一);muted 置灰为原有温和样式非回归。探针断完即删。
- **顺手**:L29 四度重演(裸 cargo build 白屏)——aivlaunch 加 `_assert_fresh_build` 结构防闸(launch 时比对 exe mtime 与 src 树最新 mtime,旧于源码即拒发;双向实测),lessons L29 记档。
- **发布**:0.8.19 已发体验渠道(staged 0.8.18→0.8.19,防同版本闸过);离线安装包未动(0.8.14 现役)。

### 返工轮 0.8.20(2026-11-05,owner 验收 0.8.19 时反馈)

- **owner 反馈**(截图):目标行不在树当前显示区域时,定位滚动把高亮行停在可视区**边缘**,"体验不好,最好让它大致居中"。
- 修法:FileTree reveal 消费处 `scrollIntoView({block:"nearest"})` → `block:"center"`——链接跳转与 Ctrl+L 按路径定位两条路径共用此处,一并居中;列表首尾行按滚动边界 clamp(VS Code 同款行为,保留)。
- **守卫首跑照出潜伏 bug**:reveal 消费条件要求父目录在 expandedFolders,而树根从不进该列表——**根级文件**的定位滚动从未生效过(0.8.19 守卫目标全在子目录,没盖住);修=TREE_ROOT bypass 一行。
- 全档:check 0/0+vitest 149/149+cargo 免跑(Rust 零改动)+phase3 **PASS×3**(130 守卫,+1 md_link_reveal_centers_row:压缩树视口 300px 造确定性滚动场景,断言目标行中心与视口中心偏差≤20px 且确有滚动);**几何+视觉双亲验**:探针 midOffset=0(精确居中)+视觉模型判读截图(居中区带/选中态/无异常),探针断完即删。0.8.20 已发体验渠道。
