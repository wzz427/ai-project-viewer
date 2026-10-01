# spec-004 · Session & Settings(关掉再开,一切还在:会话恢复 + 设置持久化)

> 状态:Ready —— 真值 = specs/INDEX.md。
> 创建:2026-10-01;Pre-Draft 结论:owner"这个就算过了吧"(spec-003 Done)+ 交接页主线指向 Phase 4;免审门适用(workflow §五 A2/A5)。
> 需求源:V1.5 §178(Phase 4 批次);完成判据:§188 Application 块 5 行 + Path Persistence 块 5 行 + §192-7。

## 〇、值不值得做

Phase 4 是 V1.5 §175–182 排期定死的第四批,判:做(应用从"每次从零"变"记得一切";Phase 2/3 的 store 已按相对路径身份设计,本批零结构迁移即接上)。

## 一、Pre-Draft 结论

- 核心选择题:无新增须问项;防抖区间(§26 建议 500–1500ms)、JSON+原子替换(§25/§26)、version=1+迁移骨架(§23)均 V1.5 已定。
- 标杆对照:Session Restore 对照 VS Code(重开恢复窗口布局/打开文件/滚动位置);Settings 对照 VS Code Settings 面板的"改即生效即记住"。
- **界面确认基线**:本批几乎无新界面;Settings 面板结构 Phase 2/3 已成型(§30 修订后的 File Tree 区已有),V1.5 §22 已含设置项明文=已确认。

## 二、需求正文(R 编号;一行 = V1.5 一节,使用者视角提要)

| R# | 需求提要 | V1.5 节 |
|---|---|---|
| R1 | 应用状态带版本号落盘为 JSON(AppState.version=1);以后结构变化走迁移,不直接破坏旧状态文件 | §23 §25 |
| R2 | 会话恢复:重启后项目标签、每项目展开的目录/置顶收藏/打开的文件页签(含激活页、Rendered\|Source 模式、滚动位置)/侧栏所在面板都还原 | §17 §178 |
| R3 | 收藏置顶与展开态持久化,身份一律项目相对路径("." 为根),不无必要绑定盘符 | §18 §19 |
| R4 | 写盘防抖:状态变化后合并延时写一次;正常退出再执行一次最终写入;写法=临时文件→Flush→原子替换,state.json 永不半截 | §26 |
| R5 | 迁移骨架就位(version 检查+迁移链位);未知新版本/损坏状态文件不崩,自愈为全新默认 | §23 |
| R6 | AppSettings 持久化:主题、查看器字号、Show system/generated folders(全局)重启保留 | §22 §30 |
| R7 | Settings UI 成型:已实现功能的设置项集中在 ⚙ 面板且全部持久化;未实现功能(editors/pdf/git 条数)的设置项不提前出现 | §22 §24 §178 |

**反例规则**:不许每次用户操作都同步写盘(§26);Git 运行态不持久化(§20,本批不涉及);恢复过程不许递归扫描完整项目、不预读文件内容(§160.1/§160.18);恢复时 5–20MB 文件不弹确认框(确认针对用户打开动作 §106,恢复是自动流程)。

## 三、验证标准(V 编号;组级指向 §188)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 R4 R6 R7 | §188「Application」块 5 行:AppState 包含 Version / Session Restore 正常 / State Write 有 Debounce / State 使用 Atomic Replace / Settings Entry 正常 | 自动(cargo+CDP) |
| V2 | R3 | §188「Path Persistence」块 5 行;落盘 JSON 断言无盘符、expandedFolders/pinnedItems/openFiles 全相对路径 | 自动(vitest+CDP) |
| V3 | R2 R6 | 端到端重启恢复(CDP 零前台,独立 state 文件):加项目→展开/置顶/开多页签(含 Source 模式+固定页签)→改主题/字号→退出→重启,以上全部还原;图片/文本内容按需重读且显示正确 | 自动(CDP) |
| V4 | R1 R4 R5 | cargo 单测:连续变化合并一次落盘(防抖);tmp 先写后换、结束后无 .tmp 残留;损坏 JSON→坏文件改名备份+默认启动;缺 version 拒为损坏;迁移骨架链(v1 空、未来版本号路由就位) | 自动(cargo) |
| V5 | R4 | 测试态隔离:AIV_TEST_PROJECT 设置且未给 AIV_STATE_FILE 时,owner 真实 state.json 读写均不发生 | 自动(cargo) |

## 四、技术实现方案

### 边界(不做清单)

| 不做 | 归属 |
|---|---|
| editors(quick/code editor、vscodeOpenMode)/ pdf.defaultZoomMode / git.recentCommitCount 设置项 UI | Phase 6/5/7(功能落地时一并出;§22 的其余设置现在都是死设置) |
| sidebarWidth 拖拽调宽 | V1.5 无交互明文(§17 只有字段);字段持久化就绪恒 260,owner 要即加(D6) |
| trustedForExecution 语义 | Phase 8(字段随 ProjectSession 落盘,默认 false) |
| Git 运行态任何持久化 | §20 明令禁止 |
| Watcher / 实时刷新 | Phase 9 |

### Rust(新模块 src-tauri/src/state/,2 个 command)

- **`load_state() -> Option<String>`**:定位状态文件 → 读 → 迁移链 → 返回 JSON 字符串。文件不存在→None;解析失败或缺 version→坏文件改名 `state.json.corrupt-<ts>` 备份后返回 None(自愈)。
- **`save_state(json)`**:更新进程内 last_state(RwLock)→ 原子写:同目录 `state.json.tmp` 写入→sync_all→rename 覆盖(std rename 在 Windows 走 MOVEFILE_REPLACE_EXISTING)。
- **退出兜底**:`Builder::build().run(callback)` 捕 RunEvent::Exit,把 last_state 再原子写一次(WebView 卸载时前端 invoke 不可靠,§26"正常退出最终写入"的保险层)。
- **测试态闸门(在同一层)**:AIV_TEST_PROJECT 非空且 AIV_STATE_FILE 未设 → load 恒 None、save 恒 no-op;AIV_STATE_FILE 给了 → 两个 command 都只碰那个文件。owner 的真实 state 永不被 GUI 测试污染,持久化回归又可重复。
- **迁移骨架 migration.rs**:`migrate(&mut Value)`:读 version;<CURRENT 抬版本(链内逐级,v1→v2 位留空示例);>CURRENT 拒(视为损坏走自愈);缺 version 拒。CURRENT_VERSION=1。
- 状态文件路径:`app_config_dir()/state.json`(AIV_STATE_FILE 覆盖);目录不存在 create_dir_all。
- 单测:原子写往返/无 tmp 残留/损坏自愈/缺 version/未来版本拒/测试态闸门/迁移链路由。

### 前端

- **`services/appState.ts`(纯函数,vitest)**:`buildAppState()` 从四大 store 白名单序列化(version/projects[id,name,rootPath,expandedFolders,openFiles 白名单,activeFileRelativePath,sidebarMode,sidebarWidth,trustedForExecution,fileTreePreferences{foldersFirst,pinnedItems}]/activeProjectId/settings[theme,viewer.fontSize,fileTree.showSystemGeneratedFolders]);`applyAppState(state)` 写回各 store。openFiles 白名单:relativePath/viewerType/markdownMode/jsonMode/pinned/scrollPosition(D7:后两个超出 §21 字面,是 §197 行为延伸);encoding/cursorLine/内容缓存不落盘。
- **启动恢复(main.ts)**:load_state → applyAppState → theme/fontSize/全局开关生效 → 逐项目 resolve 校验(失效跳过,D9)→ 恢复 expandedFolders 的每层触发一次单层 listDirectory(只到上次展开的深度,§160.1)。
- **恢复的内容懒读(D4)**:恢复只重建页签身份与模式;ActiveViewer 发现 cache miss 时触发 `ensureContentLoaded`(图片走媒体通道,文本走读盘,5–20MB 不弹确认;huge/binary tab 按存的提示态恢复不重读)——现状 cache miss 只会永远显示 Loading…,这是恢复场景的必接点。
- **防抖保存**:`$effect.root` 挂一个 effect:序列化(读到的字段即依赖,新字段进序列化自动被跟踪)→ 800ms 防抖(§26 区间中值)→ invoke save_state;`pagehide` 时立即 flush 一次。
- **作用域对齐**:showSystemFolders 从每项目树态挪到全局 settings(D5,§22 字面);sidebarMode 从 App.svelte 局部态挪进 ProjectSession(D6,§17 字面,切项目恢复各自面板)。
- **Settings 面板**:File Tree 区的 Show system folders 改作用全局;页尾 note 改为指向后续 Phase 的设置预告。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 状态聚合在前端纯函数,Rust 只收 JSON 字符串管 IO | 状态真值在 Svelte store;Rust 理解业务结构=双份必漂 | Rust 侧组装 AppState | 同上 |
| D2 | 防抖用 $effect 深跟踪序列化输出,800ms | 序列化读到的字段自动成为依赖,新增字段零成本被跟踪 | 各 mutation 手动 markDirty | 改动点散,漏一处静默丢状态 |
| D3 | 退出双保险:前端 pagehide flush + Rust RunEvent::Exit 兜底写 last_state | WebView 卸载时 async invoke 不可靠 | 只靠前端 beforeunload | 同左 |
| D4 | 恢复懒读内容,5–20MB 不弹确认 | §106 确认针对用户打开动作;恢复是自动流程,弹窗打断 | 恢复也弹确认 | 体验断点无意义 |
| D5 | showSystemFolders 全局化(§22 AppSettings 字段),foldersFirst 保持每项目(§17) | 基线字面;且无持久化期间"每项目各自的值"本就无从体现,用户无感 | 保持每项目 | 与 §22 冲突 |
| D6 | sidebarMode 入 ProjectSession(含 settings 三态);sidebarWidth 持久化恒 260、不做拖拽 | §17 字面/§30 修订;拖拽无 V1.5 明文 | 顺手做拖拽 | 范围膨胀,标"未确认"留给 owner 点头 |
| D7 | 页签 jsonMode/pinned 一并持久化 | §197 两项修订(Formatted\|Source 菜单、Pin File Tab)的行为自然延伸;丢则重启后状态全丢,用户可感 | 严格只存 §21 字面 | 教条对齐字面牺牲可感体验 |
| D8 | fontSize 入 AppSettings.viewer.fontSize,默认 13,§22 增量修订+§197 审计行随本批落 | §197 已有技术性行认领该设置,需归位进正式结构 | 塞进 ProjectSession | 字号是应用级偏好非项目会话 |
| D9 | 恢复时逐项目 resolve,失效项目静默跳过 | 项目被移动/删除是常态;§188 未列,自愈优先于报错 | 弹提示/留僵尸标签 | 无处可点的入口只添堵 |
| D10 | 测试态闸门在 Rust 命令层 | 单一闸门,前端漏设环境变量也兜得住 | 前端判断 | 两处入口(启动恢复/防抖保存)都要记得判,必漂 |

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 R4 R5 | V4 V5 | cargo 单测(tmp/自愈/版本/闸门)+ 防抖断言 | 临时目录 | ✓ |
| R3 | V2 | vitest:buildAppState 输出无盘符+白名单正确 | — | ✓ |
| R2 R6 | V3 | CDP 零前台(AIV_STATE_FILE 指向 %TEMP%):改状态→kill→重启→断言还原 | 桌面 AIV-TestProject | ✓ |
| R1 R4 R6 R7 | V1 | CDP:Settings 改动重启保留;state.json 结构含 version;连改多次观察落盘次数(防抖) | 同上 | ✓ |

缺口检查:重启恢复走 CDP connect_over_cdp + 进程重启,基建 Phase 3 已有(testing.md §1),无新通道。

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | Draft→Ready | R/V 指针化、D1–D10、覆盖矩阵;开工切分:①Rust state 模块+单测 ②前端 appState 纯函数+vitest ③接线(恢复懒读/防抖/兜底/作用域对齐) ④Settings 面板+§22 增量修订 ⑤自测+release+文档 |
