# SPEC-006-Handoff —— 右键把文件交出去:记事本 / VS Code / 资源管理器 / 浏览器 / 复制路径

> 状态:InDev(跃迁记录见 INDEX.md 那一行,本页不抄第二份)
> 创建:2026-10-10;Pre-Draft 结论出处 = V1.5 §180(Phase 6 清单)+ §130–§142(分型菜单规格)+
> §188 HANDOFF 验收块;owner 放行开工(2026-10-10 原话"收口吧,然后我操作compact,你再开始phase6"→"启动phase6")。
> 本 Phase 免审依据 docs/workflow.md §五 A2(动笔前疑问清单:无阻塞项;细节默认已标"未确认"于决策表)。

## 〇、值不值得做

- 好处:观察器看到问题后要动手,现在必须自己去开资源管理器找路径;右键直达=每次省 4–6 步。owner 全部工作流(§106 定位)就是"看→必要时进 VS Code 正式编辑",这是本应用存在的理由之一。
- 代价:约 1 个开发段(Rust 语义命令层 1 模块 + 3 个右键菜单扩条目 + 1 个设置项);可能碰坏的=现有三菜单(Pin/模式切换/Open with Default App 均在用,回归须带上)。
- 判:值→做(V1.5 §180 明列 Phase 6)。

## 一、Pre-Draft 结论

- 核心选择题:无新增(V1.5 §135–§141 已把每个菜单逐条写死;§132/§133 已定抽象与安全边界;§134 已定默认 New Window)。
- 标杆对照:菜单结构=V1.5 明文(VS Code 式分组);Explorer 语义=VS Code(文件=在父目录中选中;项目=打开文件夹窗口)。
- **界面确认**:§135–§141 菜单明文 = 已确认基线(workflow §五 A3);未含明文的细节(文件夹"Open"语义/页签菜单范围)由决策表代取默认+标"未确认"。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

| R# | 需求(使用者视角;真值 = V1.5 节号) |
|---|---|
| R1 | 文件树右键,按文件类型出现 §135–§140 的分型菜单:文本类(含 md/txt/code/json/script)=Open / Edit in Notepad / Open in VS Code / Show in File Explorer / Copy Absolute Path / Copy Relative Path / Pin;HTML 与 .url 加 Open in Browser(§136/§115);PDF = Open / Open with Default PDF App / Show / Copy×2 / Pin(§138);图片/视频/系统程序类 = Open / Open with Default App / Show / Copy×2 / Pin(§142 System App 行+§197 泛化行);EXE/MSI/二进制 = Show / Copy×2 / Pin(Run 属 Phase 8,§139/§182 不在本期);文件夹 = Open / Show / Copy×2 / Open Folder in VS Code / Pin(§140) |
| R2 | 文件页签右键,同样拿到该文件类型的移交条目(Edit in Notepad / Open in VS Code / Show in File Explorer / Copy×2;类型特有项如 PDF Default App 同步),现有条目(模式切换/Pin Tab/Open with Default App/Close)不动(§135 是"文件的菜单",页签是该文件的第二个出现面;§197 已把模式切换安在页签菜单) |
| R3 | 项目标签右键:Open in File Explorer / Copy Project Path / Open Project in VS Code,现有 Remove Project 不动;Refresh 已住 Settings(§30 修订),Trust 属 Phase 8(§141 相应行不入本期) |
| R4 | Settings 新增 "Open in VS Code":● New Window ○ Reuse Existing Window,默认 New Window,随会话持久化(§134) |
| R5 | 所有移交动作失败有反馈:VS Code 未安装 → 明确提示;外部进程启动失败 → toast(§188 Empty/Error 块) |
| R6 | Copy 动作有确认反馈(toast 含被复制内容),Relative = 项目内 `/` 分隔相对路径,Absolute = 反斜杠绝对路径 |
| R7 | `.url` 的 Open in Browser 只放行 http/https,javascript:/powershell:/cmd:/file:/shell: 一律拒绝(§115) |

**反例规则(不许做什么)**:前端不获得任何"任意可执行文件"能力——只许调语义化命令(§133);路径校验禁止 raw string startsWith,必须 canonicalize + Path starts_with(§144);不经 cmd /c 拼接启动(§188 RUN 块的 Windows 纪律)。

## 三、验证标准(V 编号;组级指向 §188 HANDOFF 块)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1 | 夹具项目右键 README.md → 菜单含 Edit in Notepad/Open in VS Code/Show in File Explorer/Copy Absolute Path/Copy Relative Path(+Open/Pin);右键 docs 文件夹 → 含 Open Folder in VS Code、无 Notepad/Default App;右键 guide.pdf → 含 Open with Default PDF App、无 Notepad/VS Code;右键 exe → 无 Notepad/VS Code/Default App(仅 Show/Copy/Pin) | 自动 |
| V2 | R1 | html 右键含 Open in Browser 且含 Edit in Notepad/VS Code(§136);.url 右键含 Open in Browser 且含 Edit in Notepad(§142 Quick Edit 列=Notepad,D7) | 自动 |
| V3 | R2 | 打开 README.md 后页签右键 → 含 Edit in Notepad/Copy Absolute Path 等移交条目,且 View Source/Pin Tab/Close Tab 仍在 | 自动 |
| V4 | R3 | 项目标签右键 → Open in File Explorer/Copy Project Path/Open Project in VS Code/Remove Project 四项在 | 自动 |
| V5 | R4 | Settings 含 VS Code 区,默认选中 New Window;切到 Reuse → 重启应用仍是 Reuse | 自动 |
| V6 | R6 | 点 Copy Absolute Path → toast 出现且文本含 `\` 绝对路径;点 Copy Relative Path → toast 含 `docs/…` 式相对路径;剪贴板读回与 toast 一致(权限允许时) | 自动 |
| V7 | R5 | 卸载路径模拟(VS Code 探测函数喂不存在目录)→ 命令返回错误文案含 "VS Code"(cargo 单测);前端 toast kind=error(phase3 断言错误路径 handler) | 自动 |
| V8 | R7 | cargo 单测:`javascript:`/`file:`/`powershell:` scheme 拒绝;`https://` 放行 | 自动 |
| V9 | R1/R3 | 真机一轮(V8 先例"真程序弹出"标准):Edit in Notepad 弹出记事本并载入该文件;Show in File Explorer 弹出资源管理器且该文件被选中;Open in VS Code 弹出 VS Code;Open in Browser 弹出默认浏览器;脚本随即关闭所开窗口(零打扰纪律:一次受控轮,不开第二轮) | 人工(受控) |
| V10 | R2 | 页签菜单 Copy Relative Path 与树菜单同源同值(同一构建函数,断言两端条目集一致) | 自动 |

> V-human 占比:V9 一条受控人工(自动 9 条),≤ 自动一半 ✓。§188 HANDOFF 12 个勾全部由 V1–V10 覆盖(ExternalEditor 抽象=代码结构+cargo 测试;无任意执行=capabilities 不含 shell-exec 类权限+命令面审)。

## 四、技术实现方案

- **Rust 新模块 `src-tauri/src/handoff.rs`**:§132 ExternalEditor trait(id/name/open_file/open_folder?)+ NotepadEditor + VSCodeEditor;语义命令 `edit_in_quick_editor` / `open_in_code_editor`(rel=null 即项目根)/ `reveal_in_explorer`(rel=null 即项目根,语义=打开文件夹窗口)/ `open_with_default_app` / `open_in_browser`(html→file URL 转换;.url→INI 解析+scheme 白名单)。全部先过 resolve 校验(canonicalize + starts_with,复用 §144 先例;文件与目录皆可,新 `resolve_handoff_target`)。启动走 opener 插件 Rust API(open_path/open_url/reveal_item_in_dir,ShellExecute 后端,无 cmd /c)与 `std::process::Command` 直启 Code.exe/notepad.exe。
- **前端服务 `src/lib/services/handoffMenu.ts`**:唯一菜单构建函数 `fileHandoffEntries(name, isDir)` → 条目数组(label+action);树菜单与页签菜单共同消费(防两份漂移)。`clipboard.ts`:navigator.clipboard 优先,execCommand 兜底,必 toast。
- **组件**:NodeContextMenu / TabContextMenu / ProjectContextMenu 挂条目;SettingsPanel 增 External Editors 区(§134 单选);settingsStore 增 `external.vsCodeNewWindow`;appState PersistedSettings 增可选 `external`(缺省=true,向后兼容);sessionRestore 收养。
- **tauri.ts**:openWithDefaultApp 改走 Rust 命令(替换 JS 字符串拼路径——顺带补上 §143 校验缺口);新增五命令包装。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 全部移交动词=Rust 语义命令,先校验后执行 | §133(前端无任意执行)+§143(一切 Read/Run/Reveal/Open 先验证);现有 JS openPath 拼串绕过了校验,本 SPEC 顺手关闭该缺口 | 继续用 JS opener capability | 路径校验会留在前端字符串层,违 §143/§144 |
| D2 | VS Code 探测序:%LOCALAPPDATA% 用户版 → Program Files → PATH 上的 code.exe;找不到=Err("VS Code not found…") | 本机实证=用户版安装;三序覆盖标准装法 | ①起 cmd `where code` ②spawn `code.cmd` | 两者都要 cmd /c(§188 禁拼);.cmd 壳需 shell 解释 |
| D3 | new_window 作为命令参数(非 Rust 侧设置态) | 设置真值在前端 settingsStore(§22 体系),Rust 无状态=零驻留(内存第一原则);参数是模式不是可执行,不破 §133 | Rust 侧持久化设置 | 双份状态必漂(AGENTS.md 一件事只住一处) |
| D4 | 文件/文件夹 "Show in File Explorer"=在父目录中选中(reveal_item_in_dir);项目 "Open in File Explorer"=打开项目文件夹窗口;文件夹 "Open"=打开该文件夹窗口 **(未确认,V1.5 无文件夹 Open 明文)** | VS Code 语义;§141 用词是 "Open"(非 Show);reveal 与 open 是两个已存在的低层动词 | 文件夹 Open=树内展开 | 展开已有箭头/双击,菜单里冗余 |
| D5 | PDF 条目名 "Open with Default PDF App";图片/视频/系统程序类 "Open with Default App"——同一 Rust 机制,标签按 §142 分型 | §138 与 §197 泛化行的原文;机制上都是 OS 关联打开 | 两个不同命令 | 无行为差异,只造复述 |
| D6 | 剪贴板=navigator.clipboard + execCommand 兜底 + toast 证词;不引 clipboard 插件 | tauri.localhost 在 Chromium 属可信源,API 可用;toast 同时满足 V6 判定与失败反馈(R5);零新依赖=零新面 | tauri-plugin-clipboard-manager | 多一个依赖与权限面;owner 复验若报失效再上(回退条件) |
| D7 | .url 右键含 Edit in Notepad/VS Code(§142 Quick Edit 列=Notepad) | §142 表 .url 行明文 | 照 HTML 菜单去 Notepad | §142 是权威规格 |
| D8 | Phase 6 菜单切片:§137 Run Script、§139 Run、§141 Trust/Untrust/Refresh Project 不做 | §180 清单无 Run/Trust(那是 §182 Phase 8);Refresh 已随 §30 修订住 Settings | 全量照抄 §137/§139/§141 | 一次只做当前 Phase(AGENTS.md) |
| D9 | 版本 0.6.2(三处),发布前核段号属己 | owner 2026-10-10 立规 0.6.x 固定递增 + L23 发版段号纪律 | 0.7.0 | 明令不跳段 |
| D10 | ExternalEditor 实例按调用构造,不缓存 VS Code 路径 | 探测=2–4 次 exists 检查(微秒级),缓存=常驻状态违内存第一原则;Notepad 无需探测 | OnceLock 缓存探测结果 | 换装/改装 VS Code 后缓存必陈旧 |

**内存账**:五命令皆 spawn-and-forget,进程退出即回收;零新驻留(菜单条目随开随建,clipboard 兜底 textarea 用后移除)。设置增 1 个布尔。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1/V2 | phase3-suite:右键四型节点,断言菜单条目集 | AIV-TestProject(已有)+ 补 html/.url/exe 夹具(make-fixtures 增) | ✓ |
| R2 | V3/V10 | phase3-suite:页签菜单条目 + 两端同源断言 | 同上 | ✓ |
| R3 | V4 | phase3-suite:项目标签右键条目集 | 同上 | ✓ |
| R4 | V5 | phase3-suite:设置默认值 + AIV_STATE_FILE 独立态重启还原 | 同上 | ✓ |
| R5 | V7 | cargo(探测函数+scheme 白名单纯函数)+ phase3 toast | 临时目录(探测)/合成字符串(scheme) | ✓ |
| R6 | V6 | phase3-suite:toast 文本 + 剪贴板读回(权限拒绝时降级只断 toast) | 同上 | ✓ |
| R7 | V8 | cargo 单测:五种 scheme 判定 | 无 | ✓ |
| R1/R3 | V9 | 受控真机一轮(记事本/资源管理器/VS Code/浏览器真弹出,随即关闭) | 本机(已核 VS Code 用户版在) | ⚠ 交付时执行 |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物(矩阵/自检/验收原话) |
|---|---|---|
| 2026-10-10 | 立项 Draft→Ready(免审,workflow §五 A2:R/V 与 V1.5 §180/§130–142/§188 逐条对上,决策表 D1–D10 齐,无疑问需确认) | 测试覆盖矩阵 10 条 |
| 2026-10-10 | Ready→InDev | — |
