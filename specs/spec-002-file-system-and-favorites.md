# spec-002 · File System & Favorites(文件树、收藏置顶、文件识别)

> 状态:Ready —— **状态与"去处"的唯一真值 = specs/INDEX.md 那一行**,本页不抄第二份。
> 创建:2026-10-01;Pre-Draft 结论出处:owner 2026-10-01 拍板"每段开发先写 Spec 再开发;Spec 内容免 owner 过目,agent 自核与原始需求对上;动笔前有疑问/要变化先跟 owner 确认";需求源 = V1.5 §176(Phase 2 批次定义)。
> **本项目适配(写法与模板的差异,依据 docs/workflow.md §五)**:需求真值是 V1.5,本 SPEC 的 R 行只挂 V1.5 节号指针 + 一句话提要,不重抄正文;V 行组级指向 §188 验收清单对应块——**禁止两套编号各写一套正文**(必漂)。

## 〇、值不值得做

- Phase 2 是 V1.5 §175–182 排期里定死的批次,"值不值"已在需求定稿时判过(出处 V1.5 §176),此处不重复判。
- 判:做(V1 roadmap 的第二步,Files 面板从壳变实)。

## 一、Pre-Draft 结论

- 核心选择题:owner 已拍——① Spec 免审、agent 自核对齐 V1.5(2026-10-01 原话"这个 Spec 我就不过目了,你自己能跟原始需求对上就行");② 有疑问/要变化,动笔前先确认(同日);③ specs 体系按指南落(根目录 specs/、spec-NNN 编号、INDEX 台账、workflow 状态机,2026-10-01)。
- 标杆对照:文件树交互对照 VS Code Explorer(展开即读一层、右键菜单、置顶区);V1.5 §30 已给定 Files 菜单的精确文案与结构。
- **界面确认**:V1.5 已含界面明文的(§30 菜单、§31 隐藏提示、§37 Pin 展示),以 V1.5 为已确认基线;V1.5 未规定的界面细节(树缩进/图标风格/空目录样式等)走 §四决策表代取默认,交付时可视化验证给 owner 看,回退条件:owner 看实物有异议 → 改决策表行 + 对应代码。

## 二、需求正文(R 编号;一行 = V1.5 一节,使用者视角提要)

| R# | 需求提要 | V1.5 节 |
|---|---|---|
| R1 | 打开项目只见第一层目录,展开哪层才读哪层,启动不递归全扫 | §27 |
| R2 | 用户看到的目录可见性,与(将来)监听哪些目录变化,是两份独立清单 | §28 |
| R3 | `.git`/`node_modules` 等 8 类默认隐藏;`dist`/`build`/`target` 默认显示 | §29 |
| R4 | ~~Files `⋯` 菜单~~(2026-10-01 修订):Folders First、Show system folders(默认 OFF)、Refresh 住进 Settings 的 File Tree 区;⚙ 点进/点回 | §30 修订 |
| R5 | 有目录被隐藏时显示"N system folders hidden",用户知道文件没丢 | §31 |
| R6 | ~~Name/Favorites 两模式~~(2026-10-01 修订):恒为 Pinned 区(手工拖拽序)+ Unpinned 区(Name 自动序) | §33 修订 §35 |
| R7 | Folders First 只作用于 Unpinned 区,Pinned 区永远按用户拖拽序混排 | §36 |
| R9 | 文件和文件夹都能 Pin;Pin 只改同父 sibling 显示序 | §37 §38 |
| R10 | Pinned 区内拖拽排序,文件文件夹混排 | §39 |
| R11 | 新出现的文件/文件夹默认 Unpinned,自动落位 | §40 |
| R12 | 可靠识别 rename 时,Pin 记录同步改并保位 | §41 |
| R13 | Pinned 条目被删,Pin 记录自动清理 | §42 |
| R14 | expandedFolders / pinnedItems 等项目内 UI 状态用项目相对路径身份(`.`=根) | §18 §19 |
| R15 | inspect_file:stat → 大小守卫 → BOM → 二进制识别 → UTF-8 严格解码 → GB18030 兜底,顺序固定 | §101 |
| R16 | 编码识别覆盖 UTF-8/UTF-8 BOM/UTF-16 LE·BE BOM/GB18030;无 BOM UTF-16 判二进制属已知限制;>20MB 不整体进 WebView | §102–§106 |

**反例规则(不许做什么)**:排序与 Pin **永不改变真实文件路径**(§176 重点红线);不提供 Full Manual Sort(§33);二进制内容不作为文本发 WebView(§104);本 Phase 文件行不可打开(Tabs/Viewer 属 Phase 3,不造假入口)。

## 三、验证标准(V 编号;组级指向 §188,新增行单独列)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1–R5 | V1.5 §188「File Tree」块 10 行逐条过(启动只请求第一层、8 类默认隐藏、dist/build/target 显示、Toggle 可恢复、提示行计数、两清单独立) | 自动(cargo+CDP) |
| V2 | R6–R13 | V1.5 §188「Favorites / Sorting」块 13 行逐条过(两种排序×Folders First 语义、文件/文件夹 Pin、同父约束、拖拽混排、新文件落位、rename 保位、delete 清理) | 自动(CDP)+人工(拖拽手感) |
| V3 | R14 | §188「Path Persistence」块中 pinnedItems/expandedFolders/不绑盘符 3 行(本 Phase 验内存态身份,写盘属 Phase 4) | 自动(单测) |
| V4 | R15 R16 | §188「File Inspection」块 11 行逐条过(流水线顺序、BOM 三种、GB18030、边界 5MB/20MB、二进制不进文本通道、大文件不冻 UI) | 自动(cargo 单测) |
| V5 | 全部 | 整个测试过程磁盘文件路径与内容零变动(排序红线) | 自动(前后快照对比) |

## 四、技术实现方案

### 边界(不做清单,防 scope 滑坡)

| 不做 | 归属 |
|---|---|
| 文件打开 / Viewer / File Tabs | Phase 3 |
| 状态写盘持久化(身份用相对路径,先住内存) | Phase 4 |
| PDF 一切 | Phase 5 |
| Explorer/编辑器打开、Copy Path | Phase 6 |
| 树上 Git 标记 | Phase 7 |
| 文件系统 Watcher(ignore 清单**结构上**现在分家,功能 Phase 9) | Phase 9 |
| 全量 Benchmark A(owner 批准才跑) | — |

### Rust 后端(2 个新 command)

- **`list_directory(root, relDir)`**:返回单层 `[{ name, is_dir, system_generated }]` + `hidden_count`;按名称打标不删除,过滤在前端(Toggle 零 IO);不递归;排序不在 Rust。
- **`inspect_file(root, relPath)`**:返回 `{ size_bytes, size_class, encoding, is_binary }`,不含内容;固定流水线 §101;新依赖 `encoding_rs`(Cargo.lock 锁定)。

### 前端

- `fileTreeStore.svelte.ts`:数据形状照 V1.5 §17/§19(expandedFolders / pinnedItems: Record<relParent, string[]> / sortMode / foldersFirst / showSystemFolders),相对路径身份,Phase 4 持久化零迁移。
- `constants/treeVisibility.ts` 与 `services/watcherIgnore.ts`(空实现+清单):§28 分离落到物理两个模块。
- FileTree/TreeItem 组件:展开才 invoke,缓存进 store;`⋯` 菜单严格照 §30;隐藏提示行;`sortEntries` 纯函数(Pinned 序优先,Unpinned 自动序,Folders First 只碰 Unpinned);节点右键 Pin/Unpin;Pinned 区 HTML5 拖拽(同父限定);Refresh 时 Pin 名单对账识别 rename(Watcher 上线后对账函数原位复用)。
- 文件行:可选中,双击无动作(D6)。
- inspect_file 本 Phase 只交付命令+单测;状态栏编码显示与 `[Open Anyway]` 确认框随 Phase 3 第一个 Viewer 落地(那些 UI 是"打开"故事的一半)。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 可见性过滤在前端,Rust 只打标 | Toggle 即时零 IO;hidden_count 免二次请求 | Rust 端过滤 | 每次切 Toggle 都要再跑一次 IO |
| D2 | 隐藏提示逐层目录显示一行 | 比只放根部准确;不引全局状态 | 只在根显示一行 | 深层隐藏目录用户看不到解释 |
| D3 | Pin 触发 = 树节点右键菜单 | 与 Phase 1 右键模式一致;V1.5 未指定 | 工具栏按钮/拖到侧栏 | 入口分散,与 §30 菜单体系不合 |
| D4 | 自然序(数字感知、大小写不敏感,前端 localeCompare numeric) | file2 < file10 符合直觉 | 码点序/Rust 端排 | "file10<File2"反直觉;显示序是前端职责 |
| D5 | 空 Folder 展开后 chevron 置灰,无占位行 | 视觉噪声控制(同 §31 精神) | "(empty)"占位行 | 加行数不加信息 |
| D6 | 文件行本 Phase 不可打开只可选中 | 打开=Tabs+Viewer=Phase 3,不造假入口 | 点击弹 toast"Phase 3 开放" | 假入口交付即拆,纯噪声 |
| D7 | rename 识别走刷新对账(消失 Pinned 名+同父恰一新增名) | Watcher 属 Phase 9,对账函数届时原位复用 | 现在就上 notify 库 | Phase 9 的活提前付,且口径未定 |
| D8 | pinned/expanded 形状照抄 §17/§19 存内存 | Phase 4 持久化零迁移 | 自造结构 | 到 P4 还要写迁移 |
| D9 | 树默认偏好:Folders First ON(Show system folders OFF 照 §30);排序无模式(见 D10) | §17 未定 UI 默认值;取 VS Code Explorer 惯例,用户最熟悉 | Folders First 默认关 | 混排对目录型项目反直觉 |
| D10 | 【2026-10-01 owner 验收反馈】排序合一(删 Name 模式)、⋯ 菜单并入 Settings、`dragDropEnabled:false` 修真拖拽 | Name 模式无独立价值;入口收敛一个 ⚙;合成 DragEvent 测不出原生拖拽,须真鼠标验证 | 保留两模式 / 保留 ⋯ / 只改测试 | 均被 owner 原话否决 |

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R15 R16 | V4 | cargo 单测(流水线各案+边界) | GB18030 中文文件、BOM×3、NULL 二进制、4.9/5/20/20.1MB、`..` 越界注入 | ✓ 方案已列 |
| R1–R5 | V1 | cargo 单测(单层性/打标)+ CDP(展开时 invoke 计数) | aiv-test-projects 造 node_modules/dist 等 | ✓ |
| R6–R13 | V2 | sortEntries 单测 + CDP(Pin/拖拽/对账) | 同上 + rename/delete 用例 | ✓ 拖拽手感留 V-human |
| R14 | V3 | store 单测 | — | ✓ |
| 全部 | V5 | 测试前后目录快照对比 | — | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | 创建(Draft) | 首版(docs/specs/ 下,后被指未按指南,重构) |
| 2026-10-01 | 重构入指南 SPEC 模板;Draft→Ready | R/V 指针化、决策依据表、覆盖矩阵;owner 免审门见 workflow.md §五 |
| 2026-10-01 | Ready→InDev→InTest | 六块全部落地(349f501 / 0816f84 / 08a9505);自测全绿:cargo 32/32、vitest 9/9、svelte-check 0/0、CDP 全链(证据 docs/testing.md §2b);release 已重建 |
| 2026-10-01 | 验收反馈返工(InTest 内) | owner 三条:D10 全落地;真鼠标拖拽实测换序成功;release 重建待复验 |
