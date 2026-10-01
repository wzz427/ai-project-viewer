# Phase 2 Spec —— File System & Favorites(开工前实现方案)

> **这份文档是什么**:每个 Phase 开工前的实现方案 + 实现决策 + 测试与验收步骤,供 owner 在动代码前审。
> **不是什么**:不是需求复述。需求真值永远在《需求文档 V1.5 FINAL》,本文只挂节号指针;两文冲突,以 V1.5 为准。
> **生命周期**:开工前写 → 开发中随实现决策更新 → Phase 验收通过后冻结为该 Phase 的实现记录(不再改,改需求走 V1.5 §193)。
> 建立背景:2026-10-01 owner 拍板"每一段开发都要先写 Spec 文档再开发",推翻建仓时"不另建 specs/"的取舍(handoff §二有改口留痕)。Phase 1 不追溯补写,其等价物 = V1.5 §175 + docs/testing.md 自测记录。

## 一、范围(V1.5 §176 全项,指针到正文)

| 功能点 | V1.5 节 | 一句话 |
|---|---|---|
| Lazy Tree | §27 | 打开项目只读第一层,展开哪层读哪层,禁止递归全扫 |
| Tree Visibility / Watcher Ignore 分离 | §28 | 两份独立清单,不得共用 |
| 默认可见性 | §29 | 默认隐藏 `.git` `node_modules` `.venv` `venv` `__pycache__` `.cache` `.next` `coverage`;默认显示 `dist` `build` `target` |
| Show system/generated folders | §30 | Files `⋯` 菜单唯一可见性 Toggle,默认 OFF |
| 隐藏提示 | §31 | "N system folders hidden",用户知道文件没丢 |
| Name Sort / Folders First | §33 §34 | A→Z;Folders First 开=目录块在前,关=混排 |
| Favorites First | §35 §36 | Pinned 区(用户手工序)+ Unpinned 区(自动序);Folders First 只作用于 Unpinned 区 |
| Pin File / Pin Folder / 同父约束 | §37 §38 | 文件夹都能 Pin;只改同父 sibling 显示序,**永不改真实路径** |
| Pinned 拖拽排序 | §39 | 同父 Pinned 区内拖拽,文件文件夹混排 |
| 新文件默认 Unpinned | §40 | 不存在"新文件插哪"的问题 |
| Pin Rename / Pin Delete | §41 §42 | 可靠识别 rename 则保位同步;删除则自动清 Pin |
| Project-relative Session Paths | §18 §19 | expandedFolders / pinnedItems 全用项目相对路径,`.` 表示根(P4 持久化的身份地基,本 Phase 先落数据形状) |
| inspect_file(检测流水线) | §101–§106 | stat → size guard → BOM → binary → UTF-8 strict → GB18030 fallback,固定顺序 |
| Large File Guard | §106 | <5MB 正常;5–20MB 提示;>20MB 不整体进 WebView(PDF 独立规则,Phase 5) |
| Binary Detection | §104 | 读头部 4–16KB 查 NULL/二进制特征;先于 GB18030 |
| Encoding Detection | §102 §103 §105 | UTF-8 / UTF-8 BOM / UTF-16 LE·BE BOM / GB18030 fallback;无 BOM UTF-16 判 Binary 属已知限制 |

**总判据(V1.5 §176 重点,一条红线)**:排序永不改变真实文件路径。

## 二、明确不做(边界,防 scope 滑坡)

| 不做 | 归属 |
|---|---|
| 文件打开 / Viewer / File Tabs(文件行只可选中,不可打开) | Phase 3 |
| 任何状态写盘持久化(pinned / expanded 先住内存,但身份用相对路径) | Phase 4 |
| PDF 相关一切 | Phase 5 |
| Show in Explorer / Copy Path / 各类 Open in 编辑器 | Phase 6 |
| 文件树上的 Git 标记(M/A/? 覆层) | Phase 7 |
| 文件系统 Watcher / Toast 更新提示(ignore 清单**结构上**现在就分两份,功能 Phase 9 才来) | Phase 9 |
| 全量 Benchmark A(owner 批准才跑) | — |

## 三、实现方案

### 3.1 Rust 后端(2 个新 command)

**`list_directory(root, relDir)`** → 单层目录条目,不递归:
- 返回 `[{ name, is_dir, system_generated }]` + 该层被可见性规则挡掉的数量 `hidden_count`;
- `system_generated` 按名称判(`TREE_HIDDEN_DEFAULT` 8 项);Rust 只**打标不删除**——过滤在前端做,Toggle 开关零 IO、隐藏提示数据现成;
- 排序不在 Rust(显示序是前端职责),Rust 只保证按目录项顺序稳定返回。

**`inspect_file(root, relPath)`** → 元数据分类结果(不含文件内容):
- 固定流水线 §101:stat(先)→ size class(normal / large 5–20MB / huge >20MB)→ BOM 检测(UTF-8 / UTF-16 LE / UTF-16 BE,§102)→ binary 检测(头部 4–16KB 查 NULL,§104)→ UTF-8 strict 解码 → GB18030 fallback(§105);
- 返回 `{ size_bytes, size_class, encoding, is_binary }`;Binary 与 >20MB 的内容**不**作为 text 发给 WebView(§104/§106);
- 新依赖:`encoding_rs`(纯 Rust,GB18030/UTF-16 解码),Cargo.lock 随提交锁定。

### 3.2 前端

- **`fileTreeStore.svelte.ts`**(新):每项目内存态。数据形状直接采用 V1.5 §17/§19:`expandedFolders: string[]`、`pinnedItems: Record<string, string[]>`(键=相对父目录,`.`=根)、`sortMode: "name" | "favorites"`、`foldersFirst`、`showSystemFolders`。全部相对路径身份 → Phase 4 持久化零迁移。
- **两份清单分家落结构**:`src/lib/constants/treeVisibility.ts` 与 `src/lib/services/watcherIgnore.ts`(空实现+清单),物理两个模块,§28 的分离在代码层面可指认。
- **FileTree / TreeItem 组件**(新):递归渲染;展开时才 `invoke("list_directory")`,结果缓存进 store;子层载入为空 → chevron 置灰不占位行(控制视觉噪声,同 §31 精神)。
- **Files `⋯` 菜单**:严格照 §30 文案与结构——Sort(Name / Favorites First 单选)、Folders First 复选、分隔线、Show system/generated folders(默认 OFF)、分隔线、Refresh。
- **隐藏提示**:每层目录若 `hidden_count > 0`,在该层子列表末尾显示一行 `N system folders hidden`。
- **排序管线**(纯前端函数 `sortEntries`):Pinned 区按 `pinnedItems[父]` 的数组序(文件文件夹混排,Folders First 不生效);Unpinned 区自动排序(Folders First 在此生效);新条目天然落 Unpinned(§40)。
- **Pin 交互**:树节点右键菜单 → Pin to Top / Unpin(复用 Phase 1 ContextMenu 组件模式);Pinned 区内 HTML5 拖拽排序,drop 目标限定同父(§38/§39)。
- **Refresh / Rename 对账**(无 Watcher 阶段的 §41/§42 落法):刷新或重新展开某层时,该层 Pin 名单对账——某 Pinned 名消失且同父恰有一个新 Unpinned 名 → 按 rename 处理,保位;否则消失即清 Pin(§42)。Watcher 上线(Phase 9)后此对账逻辑原位复用。
- **文件行**:可选中(高亮),双击无动作——打开能力属 Phase 3,本 Phase 不造假入口。

### 3.3 `inspect_file` 的 UI 消费边界

Phase 2 交付命令 + 单测;状态栏 encoding 显示(§105)、Large File 确认框(§106 的 `[Open Anyway]`)随 Phase 3 第一个 Viewer 一起落地——那些 UI 属于"打开文件"故事的一半,单独出现没有上下文。

## 四、实现决策清单(V1.5 没写死、本 Spec 拍的板——owner 可逐条推翻)

| # | 决策 | 理由 |
|---|---|---|
| D1 | 可见性过滤在前端,Rust 只打标 | Toggle 即时生效零 IO;隐藏计数免二次请求 |
| D2 | 隐藏提示逐层目录各显示一行(有隐藏才显示) | 比只放根部准确;不引入全局状态 |
| D3 | Pin 触发 = 树节点右键菜单 | 与 Phase 1 右键模式一致;V1.5 未指定触发方式 |
| D4 | 排序用自然序(数字感知、大小写不敏感,`localeCompare` numeric) | `file2 < file10` 符合直觉;前端做,Rust 不掺和 |
| D5 | 空 Folder 展开后 chevron 置灰,不渲染占位行 | 视觉噪声控制 |
| D6 | 文件行 Phase 2 不可打开,只可选中 | 打开=Tabs+Viewer=Phase 3,不造假入口 |
| D7 | Rename 识别走刷新对账 | Watcher 属 Phase 9,对账函数届时原位复用 |
| D8 | `pinnedItems`/`expandedFolders` 数据形状照抄 §17/§19 存内存 | Phase 4 持久化零迁移 |

## 五、测试与验收

**Rust 单测**(T1 档,cargo test):list_directory 单层性/打标;流水线顺序各案——UTF-8、UTF-8 BOM、UTF-16 LE/BE BOM、GB18030 中文、含 NULL 二进制、无 BOM UTF-16(判 binary,§103 已知限制)、4.9MB/5MB/20MB/20.1MB 边界;路径拒收(越出 root 的 `..` 注入)。

**前端**:svelte-check 0 错 0 警;sortEntries 纯函数单测(两区 × Folders First × 混排 × 新文件)。

**GUI 自测**(T2/T3 档,复用 testing.md §1 的 CDP+UIA 基建):fixture 用 `%USERPROFILE%\aiv-test-projects\` 造(含 `node_modules/`、`dist/`、GB18030 中文文件、5MB 与 21MB 文件各一)——启动后网络请求/命令调用只有第一层(验证不递归)、Toggle 恢复隐藏目录、提示行计数、Pin 文件+文件夹、拖拽换序、改盘上文件名后 Refresh 验证 Pin 保位、验证磁盘路径自始至终未动。

**§188 对应行**:File Tree 块、Favorites / Sorting 块、File Inspection 块、Path Persistence 块中相对路径 3 行,逐条勾进 testing.md。

## 六、提交切分(每块可独立回退)

1. Rust:list_directory + 单测;2. Rust:inspect_file 流水线 + encoding_rs + 单测;3. 前端:store + 常量分家 + sortEntries;4. 前端:Tree 组件 + Lazy 载入 + 隐藏提示;5. 前端:`⋯` 菜单 + Pin/拖拽 + rename 对账;6. GUI 自测 + §188 勾账 + 文档同步。

## 七、开工条件

owner 过目本 Spec(第一次立此规矩,先校准形态;以后默认按此模板出,有异议再改)。D1–D8 任一条可单独推翻,推翻只改本表对应行,不动其余。
