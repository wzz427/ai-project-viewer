# SPEC-011 —— Phase 10 上线前体检:性能泄漏审查 + 安全审查 + 发版准备

> Phase 10(V1.5 §184,规划内最后开发阶段,之后进 V1 验收)。前置:spec-010 已 Done。
> **本阶段禁新增产品功能**(§184 首行明文)。发版 0.7.6 起(0.7.x 递增不跳段)。
> 性能九项+安全十一项逐项过秤,审计证据表住本 SPEC §四;发版三决定 owner 已拍(§一)。

## 〇、值不值得做

§184 明列 Phase 10;九类泄漏/十一类风险虽按"内存最小化"立规逐 Phase 自律,但从无一次
**全量对账**——每类"当时以为干净"≠"今天逐调用点核过"。收益:V1 收口前最后一道系统性
体检,查出一个就赚(0.7.1/0.7.2 两层冻结根因证明"以为干净"会漏);发版三决定不定,
V1 打包无从谈起。代价:审计工时;修复可能碰任何文件(风险=审计动作本身不改行为,
只有确认的缺陷才动代码)。判:值→做。

## 一、Pre-Draft 结论

- **开工前对齐(2026-10-11,A2)**:本会话向 owner 说人话写了范围(性能体检九类/
  安全体检十一类/发版三决定+建议表),owner 原话**"开工"**=范围照 §184 全集+
  三决定按建议拍板(NSIS 安装包/不签名/不自动更新)。
- 界面:N/A——本阶段禁新增产品功能,预期零 UI 改动(修复若触及 UI 只许恢复正确行为)。
- 现状盘点:内存纪律已有基建(查看器懒加载/非激活卸载 §160.5/PDF 关页签引擎归零/
  watcher 单槽/git 防抖);安全围栏已有基建(canonicalize+根内校验/Args Array/
  git 安全旗标/opener scope)。本阶段是对账,不是从零建。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

### 性能九项(§184 Performance Review;R 通式=「该类资源在所有产生点都有明确释放路径,审计留证,发现泄漏即修+回归」)

| R# | 类别 | 审什么(产生点) |
|---|---|---|
| R1 | Event Listener Leak | 前端全部 addEventListener / Tauri listen() 调用点:随组件销毁或应用级一次性 |
| R2 | CodeMirror Leak | 编辑器实例:关页签/换字号重挂载/切走后旧实例真 destroy |
| R3 | PDF Worker Leak | pdfjs worker/引擎:关最后 PDF 页签归零(lessons L15 既有),destroy 链完整 |
| R4 | Canvas Leak | pdfjs 渲染 canvas:翻页/缩放/关闭后旧画布释放,无无界累积 |
| R5 | Page Cache Leak | 页签内容缓存:关页签/删文件/改名后缓存条目清键 |
| R6 | Watcher Leak | 监听单槽:切项目/删项目停旧,无双监听;进程退出即亡 |
| R7 | DOM Leak | 长会话开关页签/查看器后 DOM 节点数不无界增长(非激活卸载 §160.5) |
| R8 | Git Process Leak | git.exe 全部命令:超时+CREATE_NO_WINDOW,结束即退,无僵尸 |
| R9 | Child Process Leak | run.rs spawn 后即忘;**持久控制台宿主=§117/§118 有意特性非泄漏**(判定口径:程序退出后无孤儿进程存活) |

### 安全十一项(§184 Security Review;R 通式=「该攻击面所有入口都有围栏,审计留证,发现缺口即修+回归」)

| R# | 类别 | 审什么(攻击面) |
|---|---|---|
| R10 | Path Traversal | 一切文件通道(read/inspect/media/binary/tree/diff/commit):canonicalize+Project Root 内校验(§143/§144)无绕行入口 |
| R11 | URL Scheme | .url 打开/浏览器移交:http/https 白名单,无 file:/javascript: 等协议逃逸(§142) |
| R12 | SVG | 图片渲染路径不执行 SVG 内脚本(onload/script/外链);无 innerHTML 注入路径 |
| R13 | Markdown Script | markdown-it 渲染链 Raw HTML 默认禁(D4/§86–§88)未被任何后加入的特性旁路 |
| R14 | Git External Diff | 全部 git 命令带 --no-ext-diff(§70),防仓库配置触发外部程序 |
| R15 | Git Textconv | 全部 git 命令带 --no-textconv(§70),同上 |
| R16 | Command Injection | 全部 spawn 调用点 Executable+Args Array(§145),无 shell 字符串拼接 |
| R17 | Project Trust | 信任门(§126–§131):未信任时 Run/EXE 全拒,Rust 围栏与前端 UX 门双层都在 |
| R18 | EXE Launch | exe/msi 仅白名单扩展+信任后可启(§122–§124),cwd 受控 |
| R19 | Script Arguments | 脚本运行=固定路径无参数面;无 -ExecutionPolicy(§120);脚本内容不经 shell 解释 |
| R20 | Frontend Shell Permission | 前端无任意执行命令面:capabilities 最小集、CSP、invoke 清单、opener scope 全核 |

### 发版准备(§184 Release Preparation;决定已拍,动作有闸)

| R# | 决定 | 拍板 |
|---|---|---|
| R21 | Windows Installer Format = NSIS Setup EXE | owner 2026-10-11"开工"(采纳 §184 初始建议) |
| R22 | Code Sign = V1 不签 | 同上 |
| R23 | Auto Update = V1 关(体验渠道更新机制不受影响,属开发基建) | 同上 |

**反例规则**:不新增任何产品功能/UI;不为审计常驻任何监控探针(一次性 e2e 探针用完即弃);
审计动作本身不改行为——**只有确认的缺陷才动代码**;全量 Benchmark(T3)与 NSIS 实际打包
是红线闸,**不代跑**(AGENTS.md 红线"发版打包、全量 Benchmark 前 owner 点头")。

## 三、验证标准(V 编号;审计型 V=证据表+测试双轨)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1–R9(逐类) | §四审计表每类一行:产生点全清单(file:line)+释放路径判定+结论(净/漏已修);漏的修法带回归测试编号 | 自动(证据表+既有/新增测试) |
| V2 | R10–R20(逐类) | §四审计表每类一行:攻击面入口全清单+围栏判定+结论;缺口的修法带回归测试编号 | 同上 |
| V3 | R7 | 长会话探针(一次性 e2e,可弃):反复开关页签 N 轮后 DOM 节点数回落至基线带内,无单调增长 | 自动 |
| V4 | R9 | 探针:程序运行期间 spawn 的子进程(排除有意驻留的控制台宿主)在测试会话结束后无存活孤儿 | 自动 |
| V5 | R21–R23 | 三决定落 architecture 决策表+§1.5 Q1 归档;V1.5 §197 加审计行;tauri.conf NSIS 配置核对就绪 | 自动(文档核对) |
| V6 | 全部 | 既有回归全绿:phase3 64+git 33+recent 15+r3 8+pdf 19+vitest+cargo+check 0/0;动 watcher 链则 freeze-guard | 自动 |

## 四、技术实现方案

**审法**:每类先列"产生点/入口全清单"(grep 模式+人工核对),逐点判释放路径/围栏,
证据(file:line+一句话)填进下方审计表;发现的缺陷当场修+回归测试;审计表是本阶段
主产物,结论只住这一份。修复预期集中在:前端组件销毁钩子、缓存清理边角(改名/删除)、
Rust 侧命令超时面。不动架构。

**审计表(InDev 时逐行填,行=类别;状态:净/漏已修/特性非泄漏)**

| 类别 | 产生点/入口清单 | 判定 | 结论 |
|---|---|---|---|
| (待审) | | | |

| D# | 决策 | 依据 | 备选 | 排除理由 |
|---|---|---|---|---|
| D1 | 审计先行逐项留证,不建常驻监控框架 | 一次性对账;常驻探针违背内存第一原则,审计价值在"此刻全量核过" | 建泄漏探测框架 | 本阶段禁功能;探针自身=新驻留 |
| D2 | 修复零新 UI;用户可感知 bug 一律修(不称"优化") | §184 禁令+AGENTS.md 边际效益条款 | 把顺手小改塞进本阶段 | 范围漂移 |
| D3 | T3 全量 Benchmark 与 NSIS 实际打包=闸前请示,不代跑 | AGENTS.md 红线 | 直接跑 | 红线不可代拍 |
| D4 | 发版三决定=R21–R23(owner"开工"确认 §184 初始建议);V1 正式打包动作不在本 SPEC | §184"发布前明确决定"指决定本身;打包是独立动作且是红线闸 | 本阶段顺手打出安装包 | 越红线 |
| D5 | 版本 0.7.6 起(三处) | 0.7.x 递增纪律(handoff §二) | 0.8.0 | 无 owner 指令不换段 |
| D6 | Idle RAM 179MB vs §163 target 150MB:Phase 1 已判"超标全来自 WebView2 空底座,非 gate";本阶段只审"我们这边没白驻留",不承诺压到 150 | §163 定性 target 非 gate;真实判据=同场景明显低于 VS Code(留给 T3 Benchmark 判) | 强压底座 | 越权且不可达 |

**内存账(交付时报)**:预期净减或持平;每笔修复若引入新驻留须过秤并在此记一行。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1–R9 | V1 | 代码审计证据表(逐产生点)+发现即修后进对应回归 | 无 | ⚠(InDev 填) |
| R7 | V3 | 一次性 e2e DOM 节点探针(开关页签 N 轮) | AIV-TestProject | ⚠ |
| R9 | V4 | 一次性孤儿进程探针(会话结束后 psutil 差集) | 无 | ⚠ |
| R10–R20 | V2 | 代码审计证据表(逐入口)+既有 cargo/vitest 安全测试对账+缺口即修 | 无 | ⚠ |
| R21–R23 | V5 | 文档核对(architecture 决策表/Q1 归档/V1.5 §197 审计行/tauri.conf NSIS) | 无 | ⚠ |
| 全部 | V6 | 全档回归:phase3/git/recent/r3/pdf/vitest/cargo/check(+freeze-guard 若动 watcher 链) | scripts/e2e | ⚠ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-11 | 立项 Draft→Ready(A2 对齐完成:owner 看说人话范围表后原话"开工";R/V 与 §184 逐条对上,九+十一+三全覆盖) | 测试覆盖矩阵 6 行 |
