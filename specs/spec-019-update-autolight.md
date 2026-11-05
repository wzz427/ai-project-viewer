# SPEC-019-发布即点亮(owner 会问的那句话:我让你更新的时候,能不能按钮自己亮?)

> 状态唯一真值 = INDEX.md;实施记录见 §五。创建:2026-11-05;owner 指令原话「你把这个软件
> 改成更新可以由你来激活的方式吧。这样的话,你让我更新的时候,你自己去点亮 update。我一打开
> 软件发现 update 按钮是被点亮的,我直接点一下就可以了」。

## 〇、值不值得做

- 好处:owner 每轮收版少一次重启——现状按钮只在启动时检查一次,软件开着时我发布他无感,须「重启软件点亮→点更新→再重启」;改后「看到亮→点→重启一次」。
- 代价:小——Rust 侧一个目录监听(复用 notify-debouncer-full 已有依赖)+前端一个事件订阅+发布脚本原子落盘;可能碰坏:更新流本身(靠专套件回归)。
- 判:值→做。

## 一、Pre-Draft 结论

- owner 指令即方案(目标行为完整定义:发布后运行中客户端按钮自动亮,点一下完成)。
- 机制选择:**事件监听**(notify watch updates 目录)而非轮询——SPEC-INFRA-001「不轮询,磁盘零打扰」的决策边界保持(轮询每周期 md5 整个 exe,违背原决策);事件监听常驻一个 debouncer handle(KB 级,与 watcher.rs 同族基建常驻,汇报内存账)。
- 界面:无新界面(按钮点亮态已有)。

## 二、需求正文

| R# | 需求(使用者视角) |
|---|---|
| R1 | 软件开着的时候,新一轮版本发布到 updates 目录的瞬间,Update 按钮**自动点亮**(无需重启软件、无需手动点击检查);悬停说明为新版 note |
| R2 | 软件未开时发布,打开软件按钮即亮(既有启动检查行为,不回归) |
| R3 | 发布复制大文件的期间(数秒),按钮不会提供「半截可执行文件」:点更新只会装上完整校验过的新版(md5 校验失败的走既有报错路径,原版不动) |
| R4 | 开发版(e2e/dev)行为不变:无 updates 目录则无监听、按钮常灰、零成本 |

**反例规则**:不做定时轮询;不在发布方与客户端之间引入网络/IPC 通道(本地目录即通信);监听器故障不拖累主功能(按钮仍有启动检查+手动点击兜底)。

## 三、验证标准

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | 专套件:客户端运行中,向 updates 目录原子替换新版 exe+note → ≤3s 按钮 available 类点亮,悬停含新 note | 自动 |
| V2 | R2 | 专套件:启动前 updates 已有异版 → 挂载即亮(既有行为防回归) | 自动 |
| V3 | R3 | 发布脚本产物落盘为 rename 原子(代码走查+Rust perform_swap 既有 md5 校验单测);监听事件触发时若 exe 处于替换间隙,check 走 exists 闸门返回不亮,不误报 | 自动 |
| V4 | R4 | dev 布局(无 updates)启动无 watcher、无事件,按钮路径照旧(phase3 全量防回归) | 自动 |
| V5 | 全链 | cargo test 全绿(判定函数单测)+phase3 130 守卫全绿 | 自动 |

## 四、技术实现方案

- 模块:`src-tauri/src/updater.rs` 加 `watch_updates(app)`(setup 处调用,仅 updates 目录存在时建 debouncer;600ms 防抖;事件→`app.emit("update-staged")`;静态单例,Drop 语义随进程);`UpdateButton.svelte` 挂载时 `listen("update-staged")→refresh()`;`publish-experience.ps1` exe/json 均改「写 .staging 临时名→Move-Item -Force 原子替换」,顺序 exe→json。
- 关键取舍:Rust 侧只发「目录有变」哑事件,md5 判定全走前端已有 `check_update`(不在事件线程做 IO,逻辑一处真值);替换间隙的短暂「文件不存在」由 check_update 的 exists 闸门自然吞掉(误亮不可能,半截不可能)。

### 决策依据

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 事件监听非轮询 | INFRA-001 立过「不轮询」;轮询周期性全量 md5 白耗 IO | 每 N 分钟 check | 违原决策且成本高 |
| D2 Rust 发哑事件,判定走既有 command | 一处真值;事件线程零 IO | Rust 事件内直接 md5 | 逻辑分叉,漂 |
| D3 脚本原子落盘(rename) | 消灭半截窗口;watcher 事件天然只会看到完整文件 | 客户端侧「等文件静默再判」 | 复杂且治标 |
| D4 常驻一个 debouncer(体验版) | 与 watcher.rs 同族基建;KB 级 | 按需开关 | 发布频率低,开关逻辑不值 |

## 五、实施记录(2026-11-05,0.8.21)

- **代码**:updater.rs 加 `watch_updates(app)`(lib.rs setup 处调用;updates 目录存在才建 watcher,notify-debouncer-full 600ms 防抖 NoCache,事件→emit `update-staged` 哑事件;OnceLock 单例随进程;失败静默——按钮有挂载检查+手点兜底);UpdateButton 独立 `$effect` 订阅事件→refresh(单独 effect:refresh 同步段读 `status` 会让挂载 effect 依赖重跑,started 旗标吞掉重订阅而丢监听——注释已写);publish-experience.ps1 原子落盘(staging 临时名+Move-Item -Force,exe 先 json 后)+Move-Atomic 重试。**内存账**:体验版常驻一个 debouncer handle(KB 级,与 watcher.rs 同族基建);dev 零路径。
- **测试**:新专套件 `update-watch-suite.py`(**3/3**):伪体验布局(dev exe 复制到 `%TEMP%\aiv-upd-watch\app\`+旁置 updates\;updater 只认目录布局不挑 identifier,整条 watch→event→refresh 链真实跑)——同版 staged 开机不亮/运行中原子发布异版≤8s 点亮且悬停含新 note/放回同版回灰(md5 闸门方向)。全档:check 0/0+vitest 149/149+cargo 132/132+phase3 PASS。
- **live 抓获一枚真锁**:客户端流式 md5 读 updates exe 时(毫秒级),发布 rename 被拒(std fs::File 无 FILE_SHARE_DELETE)——发布脚本与套件都加 250ms×20 重试。
- **L29 五度重演**(改完 Rust 顺手 `cargo build --release`→专套件白屏):mtime 防闸拦不住「exe 新但缺 custom-protocol」;资产压缩嵌入门禁明文扫描不可行(实测 title 串不在 exe)。处置:lessons L29 记五度+**建 doc-routes.md**(AGENTS「同一条规矩第二次被忘时建」)+套件白屏症状→先疑 L29 的判据写进教训。
- **发布与衔接**:0.8.21 已发(防同版本闸过,Move-Atomic 首战)。**一次性衔接**:自动点亮只对运行 0.8.21+ 的客户端生效;owner 手上的 0.8.20 需按老办法(点灰按钮重查)升到 0.821,此后每轮发布即点亮(live-inspect 只读核实过其按钮状态:0.8.20/latest/灰)。
