# SPEC-023-标题栏版本号(左上角名字旁边能看到版本)

> 状态:见 specs/INDEX.md 那一行(唯一真值,本页不抄)
> 创建:2026-11-18;owner 需求原话=「你在软件左上角的名字旁边加一个版本号吧,这样能看到」——
> 指令已含 位置(左上角名字旁)+内容(版本号),按 spec-020 先例视为开工令,不再返场确认

## 〇、值不值得做(两栏三出口)

- 好处:owner 从界面上**从来看不到自己跑的是哪个版本**(0.8.33 他没见过;版本只活在 Update 按钮悬停/设置面板诊断行里)——验收「升到 0.8.x 没有」每次都要问。修后左上角一眼可见,任务栏悬停同显;受影响=owner 每次验收。
- 代价:纯函数 1 个+App 启动处 5 行+vitest 2 断言+phase3 1 守卫;1 小时内;可能碰坏什么:原生标题栏文字变长(无布局风险,标题栏自适应)。
- 判:值→做(owner 直接指令)。

## 一、Pre-Draft 结论

- 核心事实:应用名「AI Project Viewer」**只存在于原生窗口标题栏左上角**(tauri.conf.json `windows.title`;index.html `<title>` 同文),界面内无第二处——owner 说的"左上角的名字"就是它。
- 取数:`app_version` 命令(既有,state/mod.rs:59)返回 tauri.conf.json 版本=发布脚本核对的同一真值,零新来源。
- **界面确认**:N/A(非界面内元素,原生标题栏;owner 指令即确认)。

## 二、需求正文(R 编号)

| R# | 需求(使用者视角) |
|---|---|
| R1 | 软件启动后,左上角标题栏显示「AI Project Viewer <版本号>」(如 0.8.34);任务栏悬停同显;之后每次升级自动跟着变 |
| R2 | 版本取不到时不显示残缺后缀(不许出现「AI Project Viewer unknown」或尾随空格) |

**反例规则**:不为此加任何界面内元素/按钮/toast;不改变窗口其他 chrome。

## 三、验证标准(V 编号)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | e2e:document.title === `AI Project Viewer <tauri.conf.json 的 version>`(运行时 setTitle 与 document.title 同串写,DOM 可断言=原生标题的代理) | 自动 |
| V2 | R2 | vitest 纯函数:空串/`unknown` → 原名不带尾空格;正常版本 → `名+空格+版本` | 自动 |
| V3 | R1 | human:owner 抬头看左上角+任务栏悬停,数字与自己刚 Update 的版本一致 | 人工 |

## 四、技术实现方案

- 动 `src/App.svelte`(onMount 加一段)+ 新 `src/lib/services/appTitle.ts` 纯函数 + `index.html` 不动(运行时覆盖)。
- 关键取舍:

### 决策依据(后续翻案只翻这节)

| 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|
| D1 运行时 setTitle,不改 tauri.conf 静态标题 | 版本唯一真值已在 tauri.conf `version`,标题运行时拼接=每次发版自动跟随,零新增手工步骤 | 每次发版手改 windows.title | 第四处版本号手工同步=必漂(三处 bump 已是惯例上限) |
| D2 同时写 document.title 与原生 setTitle | 原生标题 e2e 够不着(CDP 只见 DOM),document.title 同串写入=可断言代理;若 wry 自同步则 setTitle 冗余无害 | 只写其一 | 只写原生→守卫断不了;只写 DOM→原生标题栏(owner 看的地方)不保证变 |
| D3 版本缺失/`unknown` 退回裸名 | 「unknown」上标题栏比没有更差;app_version 失败=.catch 静默,标题保持 index.html 原文 | 显示 unknown | 同左 |
| D4 不在界面内(侧栏/设置页头)另加版本字样 | owner 指的是左上角名字=原生标题栏;界面内已有设置面板诊断行 | 界面内加 | 违反指令位置;多一处要过主题/布局/双语言的成本 |

**同一条依据已同步写进它管的代码头注释**(依据和它管的东西不许分家)。

## 五、测试覆盖矩阵

| R# | V# | 测法 | 夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | phase3 守卫 `spec023_title_carries_version`:document.title 与 tauri.conf.json version 全等 | 无(套件读仓库文件) | ✓ |
| R2 | V2 | vitest:titleWithVersion 三态(正常/空/unknown) | 无 | ✓ |
| R1 | V3 | owner 抬头看+任务栏悬停 | 无 | 待 owner |

## 六、变更与验收记录

- **2026-11-18 owner 指令即开工令→同日施工毕→0.8.34 已发体验渠道(InTest)**。
- 实现:`services/appTitle.ts` 纯函数 `titleWithVersion`(blank/unknown 退裸名,D3)+ App.svelte onMount 取 `app_version` 拼「AI Project Viewer <版本>」同串写 `document.title` 与原生 `getCurrentWindow().setTitle`(D2;标题栏与任务栏悬停同显);tauri.conf 静态标题不动(D1 零第四处版本号)。施工中 svelte-check 照出重复 import(App 本就引过 getCurrentWindow),删复即绿——check 工具链自证其值。
- 测试:check 0/0+vitest **177/177**(+3 三态)+phase3 **166 PASS×3 连跑**(+1 `spec023_title_carries_version`,守卫首版误插 playwright with-block 外致 page 已关,挪进块内即绿——零产品改动);cargo/git-suite/freeze/update-watch 免跑(Rust 零改动/未触 git、updater、ActiveViewer 域)。
- 发布:0.8.34 三处 bump;staged 0.8.33→publishing;exe UTF-16 核 0.8.34 FOUND/0.8.33 absent;update.json 111B 无 BOM。
- **下一动作=owner 验收(V3 人工)**:Update 到 0.8.34(自动重启)→抬头看左上角标题栏=「AI Project Viewer 0.8.34」,任务栏悬停同显;以后每次升级数字自动跟。
