# SPEC-009-Watcher —— 文件变化实时监听:树/查看器/Git 自动刷新

> Phase 9(V1.5 §183+§76–§85)。前置:Phase 8 已 Done。**发版 0.7.0 起**(owner 2026-10-11
> 指令"版本升到0.7";SPEC-INFRA-003 D7 逃逸条款首次使用,0.7.x 固定递增不跳段)。
> 早期埋点已就位:watcherIgnore.ts(§32 清单,Phase 2 起与树可见性物理分离)、
> refreshProject 改名对账(spec-002 D7)、refreshActiveFile(§82 手动切片)、git 刷新四触发(§73)。

## 〇、值不值得做

§183 明列 Phase 9,且是"观察器"定位的核心动词:Agent 改完文件,用户今天必须手动点 ↻
才知道——每看一眼多一次点击,高频。代价:notify 依赖+激活项目一个监听线程;
风险=事件风暴(§80 已有解:忽略清单+防抖+storm 上限)。判:值→做。

## 一、Pre-Draft 结论

- **开工前对齐(2026-10-10 owner 立规)**:已发起两问(范围是否照 §183 全集 /
  自动重读=直接换新+小提示 还是 弹框先问),**未获回复——按需求文档原文默认开工**
  (范围=§183 全集;自动重读=§82 字面"自动重新读取+轻 Toast");owner 复验时一句话可翻案。
- 现状盘点:忽略清单模块已在;refreshProject 每层重列+pin 对账;refreshActiveFile 已实现
  §82 文本分支(toast 文案同款);UnsupportedViewer 已有删除态+[Close Tab](§83 字面);
  刷新通路 ↻/Ctrl+R=refreshProject+refreshGit 同源(spec-008 D12)。
- 关键默认(代拍,见决策表):防抖 400ms(§81 区间内);notify-debouncer-full(Rust 侧
  合并);storm 上限 200 事件/窗;toast 只报激活页签。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

| R# | 需求(指针) |
|---|---|
| R1 | 激活项目实时监听(§77):只 Watch Active Project;切项目即换监听目标;无项目=停 |
| R2 | 树自动更新(§76/§183):外部增/删/改名,已加载层自动重列(与 ↻ 同通路 refreshProject,不另起一套) |
| R3 | 正在看的文件被外部修改→自动重读(§82):内容换新+轻 toast"✓ <name> updated"(1–2s);滚动位置尽量保留;连续更新防抖后只报一次 |
| R4 | 后台页签缓存同步:开着未激活的文件变了→缓存换新,切过去看到的就是新的;不弹提示 |
| R5 | Git 自动刷新(§76):变化经批处理后 refreshGit(既有 ~400ms 防抖) |
| R6 | 删除处理(§83):开着的页签文件被删→页签保留+viewer"This file has been deleted."+[Close Tab];不崩、不静默关页签 |
| R7 | 改名处理(§84/§85):可靠识别(rename From/To 成对)→同步 Tab 标题/relativePath/Active File/页签缓存键/置顶 Pin/树 revealTarget;不成对→按"旧删+新增"处理 |
| R8 | Watcher Ignore(§32/§80):11 个目录不监听(与树可见性两份清单,§28);实现尽减 Event Storm |
| R9 | Debounce(§81):400ms;连续 write/rename/save 合并为一次逻辑刷新 |
| R10 | 监听语义不随树展开状态变(§79 折叠≠不监听);无轮询定时器 |

**反例规则**:不弹模态打断;storm 折叠为一次全量刷新而非逐条处理;忽略目录的事件不得跨
IPC(Rust 侧丢弃);不为非激活项目维持监听。

## 三、验证标准(V 编号)

| V# | 标准 |
|---|---|
| V1 | e2e:外部写新文件→树行自动出现(不点 ↻,≤5s);外部删除→行消失 |
| V2 | e2e:激活页签文件被外部改→viewer 内容变新+toast"✓ <name> updated"(≤5s);滚动位置恢复 |
| V3 | e2e:删除激活页签文件→"This file has been deleted."+[Close Tab] 可用且真关页签 |
| V4 | e2e:外部改名→页签标题跟新名、激活态保持;若该文件被置顶,置顶随行 |
| V5 | e2e(git-suite):外部改 tracked 文件→项目徽标/Git 面板计数自动变 |
| V6 | cargo:忽略过滤(路径段命中 11 目录拒)/rel 计算/rename 配对/storm 折叠(纯函数) |
| V7 | cargo:真监听冒烟(tempdir 写文件→批到达,超时保护) |
| V8 | vitest:affected 匹配(含目录前缀)/受影响页签筛选/toast 文案(纯函数) |
| V9 | e2e:防抖——时间窗内连续写同一文件,toast 只出现一次 |

## 四、技术实现方案

Rust 新模块 `watcher.rs`:notify-debouncer-full 400ms 单槽;回调按 §32 清单做路径段过滤,
From/To 窗口内配对(§84),>200 事件/窗折叠 storm;emit `"fs-changed"`
`{root, changed[], removed[], renames[], storm}`。命令 `start_project_watch(root)`
(canonicalize 围栏;停旧起新)、`stop_project_watch`。managed state=Mutex<Option<slot>>;
切项目/删项目由前端 effect 驱动;进程退出即亡。可测性:`spawn_watcher(root, sink)` 泛型
出 sink(生产=emit,测试=mpsc);分类/配对/折叠全部纯函数。

前端新 `watcherStore.svelte.ts`:boot 时 `listen("fs-changed")`;批次处理序=①应用改名
(页签 rel/缓存键/active/pins/revealTarget)→②refreshProject(树重列+pin 对账)→③开着的
页签按 affected 重载内容(文本/媒体/PDF/exe stat;`contentRev++` 经 ActiveViewer {#key}
重挂载换内容,§160.5 滚动恢复顺带保位)→④删除态复查(inspect)→⑤refreshGit→⑥激活页签
变了才 toast。纯逻辑抽 `watcherApply.ts` 供 vitest。接线:App $effect(激活 rootPath)→
start/stop;onMount initWatcher。

| D# | 决策 | 依据 | 备选 | 排除理由 |
|---|---|---|---|---|
| D1 | 防抖住 Rust(notify-debouncer-full 400ms),前端不二次防抖 | §80 越早合并越省 IPC;L28 隐藏窗页面定时器冻结——前端防抖在 e2e 隐藏模式不可靠 | 前端防抖 | 同上+两处超时漂移 |
| D2 | rename 识别=notify From/To 事件对(窗口内 zip) | §84"可靠识别":内核级配对比目录列表 diff 强;列表 diff(现 reconcilePins)只覆盖已缓存层 | 仅列表 diff | 深层未展开文件改名漏跟 |
| D3 | 内容更新后 viewer 经 contentRev 重挂载 | 实测 CodeViewer doc 只在 mount 建、PDF 同族——text prop 变不重画;重挂载统一走 §160.5 保位;顺带修 Ctrl+R 对代码页签不生效的旧账 | 每 viewer 内 doc 同步 | 每查看器一套同步,PDF 引擎重载更繁 |
| D4 | toast 只报激活页签的变更 | §82 主体=当前打开文件;后台静默换缓存防横幅刷屏(owner 厌恶 clutter) | 每文件一 toast | agent 批量写→刷屏 |
| D5 | storm 上限 200 事件/窗→折叠为一次全量刷新 | §80;一次 refreshProject+refreshGit 与 ↻ 等价、有界 | 无上限 | 监视目录外的风暴(手滑写爆)拖垮 UI |
| D6 | 监听单槽住 Rust 状态,前端只 start/stop | 起新必停旧,原子不留双监听;内存最小(一项目一 watcher) | 前端管多槽 | §77 只要一个 |
| D7 | 版本 0.7.0(三处) | owner 2026-10-11"版本升到0.7"(D7/INFRA-003 逃逸条款首次使用) | 0.6.14 | owner 明令换段 |
| D8 | 忽略清单 Rust 常量+TS watcherIgnore.ts 双份(注释互指) | Rust 过滤须本地判定;两清单本就"物理分离"(§28)非复述漂移型 | 跨 IPC 查询 | 每事件一次反向 IPC 荒谬 |
| D9 | e2e 断言用 ≤5s 轮询(400ms 防抖+文件系统时延) | Windows FS 事件时序抖动;硬 sleep 会 flaky | 固定 sleep | 慢机误红 |

**内存账**:watcher=激活项目一个(debouncer 线程+内核句柄,切走即 drop);无新前端定时器
(防抖在 Rust 线程);contentRev=每页签一个整数;重载即换旧引用释放,无新增驻留。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R8 | V6 | cargo 纯函数:忽略过滤/rel/rename 配对/storm 折叠 | 无 | ⚠(方案) |
| R1 | V7 | cargo 冒烟:spawn_watcher+mpsc,写文件→批到达 | tempfile | ⚠(方案) |
| R4/affected | V8 | vitest:watcherApply 纯函数 | 无 | ⚠(方案) |
| R2 | V1 | e2e:外部增删文件树自动跟 | AIV-TestProject | ⚠(方案) |
| R3 | V2/V9 | e2e:激活页签重读+toast+防抖一次 | 同上 | ⚠(方案) |
| R6 | V3 | e2e:删除态+Close Tab | 同上 | ⚠(方案) |
| R7 | V4 | e2e:改名跟页签标题/置顶 | 同上 | ⚠(方案) |
| R5 | V5 | e2e(git-suite):徽标自动变 | %TEMP% git 夹具 | ⚠(方案) |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-11 | 立项 Draft→Ready(R/V 与 V1.5 §183+§76–§85 逐条对上;对齐两问未获复,按基线默认开工,见 §一) | 测试覆盖矩阵 8 行 |
