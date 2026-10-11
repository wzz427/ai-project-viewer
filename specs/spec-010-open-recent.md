# SPEC-010-Open Recent(加项目时,一键找回最近打开过的文件夹)

> 状态:InDev —— **状态与"去处"的唯一真值 = INDEX.md 那一行**,本页不抄第二份
> 创建:2026-10-11;Pre-Draft 讨论结论出处:owner 当日指令"这个软件再增加一个 Open Recent
> 功能……请考虑清楚 Open Recent 放在什么地方,想清楚交互后再跟我说,待我确认再开发"→ 交互
> 设计(入口/记录规则/空态页附赠)当面过目 → owner 原话**"开工"**。

## 〇、值不值得做(两栏三出口,一行各句)

- 好处:每次加项目都要在资源管理器对话框逐级导航;复开此前项目的场景高频(移除即丢,找回
  成本=完整路径导航)。10 条最近列表把"重复开同一批文件夹"从十几次点击降到 1 次。影响所有
  加项目操作,无人群例外。
- 代价:约一天开发+测试;触碰点=+ 号/空态页(新增组件)、状态文件新增**可选**字段(旧文件
  自愈)、addProjectFromPath 多一处记录调用;可能碰坏的:现有添加/去重/会话恢复链路行为
  不变(纯增量,记录点在成功路径末端)。
- 判:值→做。

## 一、Pre-Draft 结论(2026-10-11,owner 已拍板)

- 核心选择题:入口放哪 → **+ 号两段式菜单**(独立按钮嫌挤、右键 + 嫌藏深,owner 过目方案
  后"开工");空态页要不要同款 → **要**(方案内一并确认);上限条数 → **10**(owner 原话
  "最多 10 个不同的文件夹")。
- 标杆对照:VS Code(File→Open Recent / Welcome Recent);同款 MRU+去重+失效项置灰;
  差异:不做右键子菜单,行内悬停 ✕ 删单条 + 底部 Clear。
- **界面确认**:2026-10-11 交互设计(菜单草图+记录规则+空态页附赠)已当面过目,owner
  原话"开工"。

## 二、需求正文(R 编号;使用者视角;正文真值=V1.5 §198,本表为提要)

| R# | 需求(使用者视角) |
|---|---|
| R1 | 成功打开一个文件夹为项目(任一入口)→ 它进"最近"列表最前;再开同一文件夹只挪到最前、不重复;最多 10 条,满了挤掉最旧(§198-a) |
| R2 | 最近列表非空时,点项目栏 + 号 → 弹小菜单而非直接开选框:Browse for Folder… 永远第一项,其下 Open Recent 列表,底部 Clear Recent |
| R3 | 最近列表为空(首用)→ 点 + 仍是老行为,直接打开文件夹选择框,零变化 |
| R4 | 点最近条目 = 打开该项目;若它已打开 → 切到它的页签 + 现有 already-open 提示 |
| R5 | 悬停条目出 ✕,点 ✕ 只删该条记录(不动任何项目);Clear Recent 清空全部记录 |
| R6 | 文件夹已删/已挪 → 条目置灰仍可点,点击给现有 "Cannot open folder" 错误提示 |
| R7 | 从项目栏移除项目,最近列表不动(删掉的项目可一键找回——本 SPEC 最值场景) |
| R8 | 最近列表随状态文件持久化,重启仍在 |
| R9 | 一个项目都没有的空白页,最近列表非空时在 Open Folder 按钮下方显示同一份列表,点击行为同 R4、置灰同 R6;空态页不做管理操作(§198-b) |

**反例规则(不许做什么)**:不弹模态;会话恢复(启动时回放已开项目)**不**记录最近——只有
用户主动打开动作记录(否则每次重启全量挪前,MRU 语义被污染);空态页不提供 ✕/Clear(管理
操作只住 + 菜单一处);不为置灰项做实时文件系统监听(打开菜单时查一次即止)。

## 三、验证标准(V 编号;可判定)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | e2e:预置 11 条 recents + 启动自动加第 12 个文件夹 → + 菜单恰 10 条、新加者在首、最旧两条消失 | 自动 |
| V2 | R2 | e2e:有记录时点 + → 菜单出现;Browse 为第一项;Clear 在底部 | 自动 |
| V3 | R3 | e2e:Clear 后保存的状态文件 recentFolders 为空且菜单不再渲染;"+ 直接开选框"分支不实点(防桌面弹原生对话框),由同函数路径+人工首用体验覆盖 | 自动 + V-human |
| V4 | R4 | e2e:点未打开条目 → 新项目页签出现并激活;点已打开条目 → 切换 + already-open toast | 自动 |
| V5 | R5 | e2e:✕ 一条 → 菜单该行消失且保存文件少一条;Clear → 保存文件为空 | 自动 |
| V6 | R6 | e2e:预置不存在路径 → 该行带置灰类;点击 → error toast,应用不崩 | 自动 |
| V7 | R7 | e2e:预置"recents 含路径 P 但 P 不是任何已开项目"→ 重启后 P 仍在列表(列表与项目生命周期隔离);移除代码路径零调用 recent API(结构走查,removeProject 与 recentStore 无依赖) | 自动 + 走查 |
| V8 | R8 | e2e:记录若干条 → 杀实例重启(同状态文件)→ + 菜单条目仍在 | 自动 |
| V9 | R9 | e2e:空项目状态 + 预置 recents 启动 → 空态页出现 Recent 列表;点条目 → 项目打开、空态消失 | 自动 |
| V10 | R1 | vitest insertRecent 纯函数:去重挪前 / 满 10 挤最旧 / 空表 | 自动 |
| V11 | R8 | vitest appState:recentFolders 超 10 读取截断、非字符串丢弃、字段缺失兼容旧文件、build 非空才写 | 自动 |

## 四、技术实现方案

- **Rust**:`project/manager.rs` 增 `paths_exist`(async 命令 + spawn_blocking——L35 纪律,
  任何文件系统访问不进主线程;`Vec<String> → Vec<bool>`,`metadata().is_dir()` 判定,文件/
  不存在同为 false);`lib.rs` 注册。
- **前端**:
  - `services/recentList.ts`:纯函数 `insertRecent(list, path, cap=10)`(vitest 直测)
  - `stores/recentStore.svelte.ts`:`recentState` + record/remove/clear/restore
  - `services/appState.ts`:`AppStateV1.recentFolders?: string[]` 可选;build 非空才写;
    parse 自愈(asStrArray + slice 10)
  - `services/stateSync`:快照带 recentFolders;`services/sessionRestore`:恢复时
    restoreRecentFolders(**只恢复不记录**,反例规则)
  - `stores/projectStore.addProjectFromPath`:resolve 成功的两个分支(新加 / 已有切换)
    各调一次 recordRecentFolder
  - `components/ProjectTabs/AddProjectMenu.svelte`:锚定菜单(clampMenu 复用);挂载时
    一次 `paths_exist` 置灰;Browse / Open Recent 列表(行内悬停 ✕)/ Clear
  - `ProjectTabs.svelte`:+ onclick 分支(recents 空 → addProjectViaPicker,否则开菜单)
  - `EmptyState.svelte`:非空时 Open Folder 下渲染同一份列表(只读,点击=打开)
- **e2e 驱动法**:不驱动原生选框(L7 红线)——预置状态文件(含 recentFolders)+ 环境变量
  自动加项目两条路覆盖全部 V。

### 决策依据(后续翻案只翻这节)

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 记录时机=用户主动打开成功(含切换到已开项目) | MRU 语义=人的动作排序 | 会话恢复也记录 | 每次重启全量挪前,历史被人手之外的东西洗掉 |
| D2 身份=resolve 后 canonical 路径 | 与项目去重同一真值,大小写/尾斜杠天然同条 | 原始字符串直存 | 同一文件夹会记成多条 |
| D3 置灰=菜单打开时查一次 paths_exist | ≤10 次 metadata,微秒级 | 常驻监听文件系统 | 为装饰性置灰付监听成本,违反内存最小化第一原则 |
| D4 e2e 不实点"+ 空表开选框"分支 | 原生文件夹对话框无法脚本驱动,弹在 owner 桌面即红线 | 测试模式拦选框 | 为测试改产品行为,得不偿失 |
| D5 cap 双侧夹(写入 insertRecent 截断 + 读取 parse 自愈截断) | 手改状态文件/异常路径不留超长列表 | 只写侧截断 | 旧 bug 模式:只堵一头,另一头必漂 |
| D6 空态页只读 | 管理操作一处真值(+ 菜单) | 空态页也放 ✕/Clear | 两处管理入口,行为必漂 |

**内存账**:常驻新增=≤10 个字符串;菜单打开时一次性布尔回收;零新增定时器/监听(持久化
搭 stateSync 现有 800ms 防抖车)。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1, V10 | e2e+vitest | 12 个临时项目目录 + 预置状态文件 | ✓ |
| R2 | V2 | e2e | 预置状态文件 | ✓ |
| R3 | V3 | e2e 断言+人工首用 | — | ✓ |
| R4 | V4 | e2e | 预置状态文件 | ✓ |
| R5 | V5 | e2e | 预置状态文件 | ✓ |
| R6 | V6 | e2e | 预置含死路径状态文件 | ✓ |
| R7 | V7 | e2e+走查 | 预置状态文件 | ✓ |
| R8 | V8, V11 | e2e+vitest | 同一状态文件两轮启动 | ✓ |
| R9 | V9 | e2e | 空项目+预置 recents 状态文件 | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物(矩阵/自检/验收原话) |
|---|---|---|
| 2026-10-11 | Draft→Ready | 自核:R1–R9 与 owner 过目方案逐条对上(菜单结构/记录规则/空态页/置灰/✕+Clear);矩阵 9/9 ✓;疑问零(交互已当面拍板) |
| 2026-10-11 | Ready→InDev | 依赖零新增(全部现有基建);开工原话见页首 |
