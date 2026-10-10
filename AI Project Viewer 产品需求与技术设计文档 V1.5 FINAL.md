# AI Project Viewer 产品需求与技术设计文档

**版本：V1.5 FINAL**  
**状态：V1 唯一有效 Development Baseline**  
**首发平台：Windows 11**  
**产品类型：本地桌面应用**  
**推荐技术栈：Tauri 2 + Rust + Svelte + TypeScript**

> **版本规则**
>
> 本文档是 AI Project Viewer V1 唯一有效的开发、测试和验收规格。
>
> V1.0、V1.1、V1.2、V1.3、V1.4 均视为历史版本，不得再作为开发依据。
>
> V1.5 采用 V1.4 保守增量修订方式形成：除本文明确修改的条目外，V1.4 已确认的产品边界、性能原则、安全规则和功能要求全部继承。

---

# 1. 产品背景

传统软件开发模式：

```text
人
↓
编写代码
↓
IDE 辅助
```

AI Agent 编程模式正在逐渐变成：

```text
人提出任务
↓
Codex / ZCode / Claude Code 等 Agent
↓
Agent 修改项目
↓
人阅读、审查、运行
↓
必要时人工修改
↓
继续给 Agent 指令
```

人在开发工具中的高频工作因此逐渐从：

> 长时间亲自编写代码

转向：

> 持续观察项目。

主要需求包括：

- 查看项目文件树；
- 阅读 Markdown；
- 阅读 PDF；
- 查看代码；
- 查看 TXT / JSON / YAML 等文本文件；
- 查看 Git 状态；
- 查看 Agent 修改了哪些文件；
- 查看 Git Diff；
- 查看最近 Commit；
- 打开 Web 页面；
- 执行 PowerShell / CMD / BAT；
- 运行 EXE；
- 偶尔快速修改少量文本；
- 必要时进入 VS Code 正式编辑。

VS Code 能完成上述工作，但同时承担大量完整 IDE 能力，包括：

- Extension Host；
- Language Server；
- Terminal；
- Debugger；
- 插件系统；
- Workspace；
- 搜索及索引；
- 完整 Git Client；
- 其他 IDE 基础设施。

对于 Agent-first Programming 工作流，其中大量能力并非持续需要，却会带来额外内存和后台资源占用。

因此开发：

# AI Project Viewer

---

# 2. 产品定位

本产品不是：

> 轻量版 VS Code。

而是：

> **面向 Agent-first Programming 的轻量级项目观察与控制工具。**

---

# 3. 一句话产品定义

> **AI Project Viewer 是一款面向 AI Agent 编程工作流的轻量级、多项目桌面观察器，通过项目阅读、Markdown/PDF 查看、Git Review、Web/脚本/EXE 运行，以及与 Notepad、VS Code 和 Windows 系统工具的快速交接，使用户无需长期运行完整 IDE，也能够高效观察和控制多个 AI 开发项目。**

---

# 4. 四个核心动作

V1 所有功能原则上必须属于以下四类之一：

```text
READ
REVIEW
RUN
HANDOFF
```

无法合理归入以上四类的功能，原则上不进入 V1。

---

## 4.1 READ

负责阅读：

- 项目文件树；
- Markdown；
- PDF；
- TXT；
- LOG；
- CSV；
- JSON；
- YAML；
- TOML；
- Python；
- JavaScript；
- TypeScript；
- HTML；
- CSS；
- Rust；
- Go；
- Java；
- C / C++；
- PowerShell；
- CMD / BAT；
- SQL；
- 图片；
- 其他 Text-like 文件。

---

## 4.2 REVIEW

负责观察项目 Git 状态以及 Agent / 人工操作造成的变化：

- Branch；
- Upstream；
- Ahead / Behind；
- Working Tree；
- Modified；
- Added；
- Deleted；
- Renamed；
- Untracked；
- Conflict；
- Staged；
- Unstaged；
- Git Diff；
- Recent Commits。

---

## 4.3 RUN

负责快速启动项目中的成果或辅助程序：

```text
.html / .htm
→ Default Browser

.url
→ Default Browser

.ps1
→ PowerShell Console

.cmd / .bat
→ CMD Console

.exe
→ Windows Process
```

RUN 只负责：

> 启动。

不因此建设：

- Terminal；
- Runtime Manager；
- Debugger；
- Process Console；
- Python Environment Manager；
- Node Environment Manager。

---

## 4.4 HANDOFF

本应用不适合完成的任务快速交给系统或专业工具。

### Quick Edit

```text
Notepad
```

适合少量文本修改。

### Full Edit

```text
VS Code
```

适合正式开发。

### System Handoff

包括：

- File Explorer；
- Default Browser；
- System Default App；
- Default PDF Reader。

---

# 5. V1 明确不做

V1 禁止开发：

- 内置代码编辑；
- IntelliSense；
- LSP；
- 自动补全；
- Refactor；
- Debugger；
- 内置 Terminal；
- 插件系统；
- Extension Marketplace；
- 内置 AI Agent；
- Git Stage；
- Git Unstage；
- Git Commit；
- Git Push；
- Git Pull；
- Git Sync；
- Git Discard；
- Git Merge；
- Git Rebase；
- Git Conflict Resolver；
- Python Environment Manager；
- Node Environment Manager；
- WSL Environment Manager；
- Package Manager；
- Build System；
- 内置 Web Browser；
- 通用 Process Manager；
- Full Manual File Tree Sort。

即使 CodeMirror 已经存在：

> 也不得因为实现简单而开启编辑能力。

---

# 6. 核心设计优先级

> 【2026-10-02 增量修订,owner 立规】**"低资源占用"升级为全程秉承的第一实现原则:内存最小化。**
> 开发过程中每一个决策(选型/数据结构/缓存策略/生命周期)都要过这道秤:
> 能不驻留的不驻留、能延迟加载的延迟加载、用户关闭的就真正释放;
> "先做完再优化内存"不被接受——内存账在动笔时就记。

```text
正确
>
稳定
>
安全
>
低资源占用(内存最小化,全程第一实现原则)
>
阅读与审查体验
>
功能数量
```

---

# 7. 总体 UI

V1 不采用 VS Code 式永久竖向 Activity Bar。

采用：

# Sidebar Header Tabs

整体结构：

```text
┌──────────────────────────────────────────────────────────────┐
│ QuantSystem ● │ GewuCode ✓ │ EnglishAgent ● │ +             │
├─────────────────────┬────────────────────────────────────────┤
│ Files   Git [7]   ⚙ │ README.md │ strategy.py │ report.pdf  │
│ ──────────────────  ├────────────────────────────────────────┤
│                     │                                        │
│ ★ README.md         │                                        │
│ ★ architecture.md   │             Active Viewer              │
│                     │                                        │
│ ▾ src               │                                        │
│   M strategy.py     │                                        │
│   A risk.py         │                                        │
│                     │                                        │
│ ▾ docs              │                                        │
│   M design.md       │                                        │
│                     │                                        │
├─────────────────────┴────────────────────────────────────────┤
│ main ↑2 ↓0                           UTF-8                   │
└──────────────────────────────────────────────────────────────┘
```

---

# 8. Sidebar Header

V1：

```text
Files     Git [7]                              ⚙
```

### Files

显示项目文件树。

### Git [7]

显示当前项目 Git Review。

### Settings

`⚙` 进入 Settings。

Settings 不是高频工作区，因此不作为 Sidebar Tab。

---

# 9. Git Badge

Git Badge 必须使用普通 UI Badge。

示例：

```text
Git [7]
```

规则：

```text
0
→ 不显示 Badge

1–99
→ 显示真实数字

>=100
→ 显示 99+
```

例如：

```text
Git [99+]
```

Badge 表示：

> 当前 Project Scope 内存在变化的**唯一文件路径数量**。

如果同一文件同时存在：

- Staged Changes；
- Unstaged Changes；

则该文件在 Badge 中：

> 只计算一次。

Badge 不表示：

> 尚未 Push 的 Commit 数。

---

# 10. Project Tabs

顶部：

```text
QuantSystem ●
GewuCode ✓
EnglishAgent ●
+
```

Git Repository：

```text
✓
当前 Project Scope 没有文件变化

●
当前 Project Scope 存在文件变化
```

Project Tab 不显示精确 Changed File 数量。

---

# 11. 非 Git 项目

如果项目目录不属于 Git Repository：

> 不显示 `✓` / `●`。

例如：

```text
NotesProject
```

而不是：

```text
NotesProject ✓
```

---

# 12. 非活动项目状态

Active Project：

> Git State 要求及时刷新。

Inactive Project：

> 可以显示 Last Known State。

不要求后台始终实时监控全部项目。

---

# 13. 添加项目

点击：

```text
+
```

调用 Windows Folder Picker。

例如：

```text
D:\Projects\QuantSystem
```

默认项目名：

```text
QuantSystem
```

即 Folder basename。

---

# 14. Project 去重

同一个实际目录不得重复添加。

添加前：

```text
canonicalize Project Root
```

如果已经存在：

> 切换至已有 Project Tab。

不创建重复 Session。

---

# 15. Remove Project

Remove Project 只表示：

> 从 AI Project Viewer 项目列表移除。

绝不允许删除真实磁盘目录。

---

# 16. Single Instance

> 【2026-10-02 增量修订;2026-10-09 owner 澄清修正】窗口关闭行为:点关闭=**隐藏到系统托盘**
> (任务栏右下角时钟旁的通知区;主任务栏不再占位,应用继续运行)。托盘图标**单击=恢复窗口**;
> **右键菜单 = Show / Exit,Exit 是唯一真正退出入口**(退出前照常落盘会话状态)。
> 初版曾按"最小化到任务栏主区"实现,owner 指正目标为系统托盘后改。


V1 默认：

# Single Instance

再次启动：

> 激活已有应用窗口。

目的：

- 防止重复 Watcher；
- 防止重复 Git 操作；
- 防止多个实例同时写 State；
- 防止无意义 RAM 翻倍。

---

# 17. ProjectSession

> 【2026-10-01 增量修订】`sidebarWidth` 的交互澄清:侧栏右缘可拖拽调宽(范围 200–600,
> 拖动中全局 col-resize 光标;分隔条可聚焦,←/→ 键盘步进 16px);宽度按项目记忆并持久化。
> 出处:owner 验收 Phase 4 时拍板"要拖拽"。

建议：

```typescript
interface ProjectSession {
  id: string
  name: string
  rootPath: string

  expandedFolders: string[]

  openFiles: FileTabState[]
  activeFileRelativePath?: string

  sidebarMode: "files" | "git"

  sidebarWidth: number

  trustedForExecution: boolean

  fileTreePreferences: {
    sortMode: "name" | "favorites"
    foldersFirst: boolean

    pinnedItems: Record<string, string[]>
  }
}
```

---

# 18. Session 路径持久化规则

所有属于 Project 内部的持久化 UI Path，应优先使用：

> Project-relative Path。

包括：

- `expandedFolders`；
- `activeFileRelativePath`；
- `FileTabState.relativePath`；
- `pinnedItems` 的父目录 Key；
- `pinnedItems` 中的 Item Path。

例如：

```typescript
expandedFolders: [
  "src",
  "docs",
  "src/components"
]
```

而不是：

```text
D:\Projects\MyApp\src
```

运行时可以计算 Absolute Path。

持久化状态不应无必要绑定盘符。

---

# 19. pinnedItems

使用 Project-relative Path。

例如：

```typescript
pinnedItems: {
  ".": [
    "README.md",
    "architecture.md",
    "src"
  ],

  "docs": [
    "design.md"
  ]
}
```

`.` 表示：

> Project Root。

---

# 20. Git Runtime State

Git State 不持久化为 Current Truth。

```typescript
interface RuntimeGitState {
  isRepository: boolean

  gitRoot?: string
  projectScopeRelativeToGitRoot?: string

  branch?: string

  ahead?: number
  behind?: number

  changedFileCount: number

  files: GitFileState[]

  refreshedAt: number
}
```

应用启动：

> 重新读取 Git。

不得把昨天的 Git 状态直接当成今天的实时状态。

---

# 21. FileTabState

```typescript
interface FileTabState {
  relativePath: string

  viewerType:
    | "markdown"
    | "pdf"
    | "text"
    | "code"
    | "json"
    | "image"
    | "diff"
    | "url"
    | "binary"
    | "unsupported"

  markdownMode?: "rendered" | "source"

  scrollPosition?: number
  cursorLine?: number

  encoding?: string

  pdfState?: {
    page: number
    zoom: number
    scrollPosition?: number
  }
}
```

Absolute Path：

> Runtime 根据 Project Root + relativePath 计算。

---

# 22. AppSettings

> 【2026-10-01 增量修订】新增 `viewer.fontSize`(默认 13):查看器字号设置,
> 承接 Phase 3 验收轮落地的字号控制(§155 UX 范围),随 Phase 4 AppSettings 持久化。

```typescript
interface AppSettings {
  theme: "system" | "light" | "dark"

  editors: {
    quickEditor: "notepad"

    codeEditor: "vscode"

    vscodeExecutable?: string

    vscodeOpenMode:
      | "new-window"
      | "reuse-window"
  }

  fileTree: {
    showSystemGeneratedFolders: boolean
  }

  viewer: {
    fontSize: number
  }

  pdf: {
    defaultZoomMode:
      | "fit-width"
      | "fit-page"
      | "100%"
  }

  git: {
    recentCommitCount: number
  }
}
```

默认：

```text
theme = system

quickEditor = notepad

codeEditor = vscode

vscodeOpenMode = new-window

showSystemGeneratedFolders = false

viewer.fontSize = 13

pdf.defaultZoomMode = fit-width

git.recentCommitCount = 20
```

---

# 23. AppState

必须显式定义版本号：

```typescript
interface AppState {
  version: number

  projects: ProjectSession[]

  activeProjectId?: string

  settings: AppSettings
}
```

V1 初始：

```text
version = 1
```

目的：

以后状态结构变化时可以：

```text
v1
↓
migration
↓
v2
```

而不是直接破坏旧状态文件。

---

# 24. Phase 1 Settings

Phase 1 只实现：

```text
⚙ Settings Entry
```

允许：

- Placeholder；
- 或 Theme Only。

完整 Settings：

> Phase 4 实现。

---

# 25. State Persistence

V1 使用：

```text
JSON
```

不引入数据库。

---

# 26. State 写盘

禁止每次用户操作都同步写盘。

采用：

```text
State Change
↓
Debounce
↓
Serialize
↓
Write Temporary File
↓
Flush
↓
Atomic Replace
```

建议：

```text
500–1500ms debounce
```

正常退出：

> 再执行一次最终写入。

---

# 27. File Tree：Lazy Loading

文件树必须：

# Lazy Loading

禁止项目打开时递归扫描完整项目。

例如初始：

```text
Project
├─ src >
├─ docs >
├─ scripts >
└─ tests >
```

只有用户展开：

```text
docs >
```

才读取这一层。

---

# 28. Tree Visibility 与 Watcher Ignore 分离

这是两个完全独立的概念。

### Tree Visibility

决定：

> 用户是否看到该目录。

### Watcher Ignore

决定：

> 是否实时监听该目录变化。

不得共用同一份 Ignore List。

---

# 29. 默认 Tree Visibility

默认隐藏：

```text
.git
node_modules
.venv
venv
__pycache__
.cache
.next
coverage
```

默认显示：

```text
dist
build
target
```

原因：

```text
dist/index.html
→ 可能 Open in Browser

build/
→ 可能阅读构建产物

target/debug/app.exe
→ 可能 Run
```

---

# 30. 显示隐藏目录

> 【2026-10-01 增量修订,owner 验收反馈】原 Files `⋯` 菜单取消,内容并入 Settings
> (⚙ 点击进入,再点 ⚙ 自动切回 Files 树);排序两选项合一后 Sort 单选组撤销(见 §33 修订)。

> 【2026-10-10 增量修订,owner 指令】Refresh 入口由 Settings 迁至**侧栏头部 ⚙ 左侧的 ↻ 图标**
> (不显示单词;点击必有可见反馈=图标旋转;无项目时隐藏)。Settings → File Tree 区仅保留排序与可见性。

Settings → File Tree：

```text
☑ Folders First

☐ Show system/generated folders
```

`Show system/generated folders` 一个可见性 Toggle。

默认：

```text
OFF
```

---

# 31. 隐藏提示

如果确实有目录处于隐藏状态：

可显示：

```text
6 system folders hidden
```

用户应明确知道：

> 文件未丢失，只是当前没有显示。

---

# 32. Watcher Ignore

Watcher 默认可忽略：

```text
.git
node_modules
.venv
venv
__pycache__
.cache
.next
coverage
dist
build
target
```

因此：

> Tree 可见性和 Watch 状态可以不同。

例如：

```text
dist
```

可以显示，但不实时 Watch。

---

# 33. 文件树排序

> 【2026-10-01 增量修订,owner 验收反馈】取消 Name / Favorites First 两种模式,
> 合并为**单一排序制**:Pinned 区(用户手工序,§35)+ Unpinned 区(按 Name 自动序,§34)。
> Pin 即置顶,无需切模式——原 Name 模式(置顶不生效的纯排序)无独立价值,删除。

排序恒为：

```text
Pinned Area(手工拖拽序)
↓
Unpinned Area(Name 自动序)
```

不提供：

> Full Manual Sort。

---

# 34. Name Sort

自动：

```text
A → Z
```

`Folders First`：

### 开启

```text
Folders A-Z
↓
Files A-Z
```

### 关闭

文件和文件夹：

> 按统一名称顺序混排。

---

# 35. Favorites First

分为：

```text
Pinned Area
+
Unpinned Area
```

### Pinned Area

用户决定顺序。

### Unpinned Area

继续自动排序。

---

# 36. Favorites First 中 Folders First 的精确规则

这是 V1.5 明确规则。

### Pinned Area

`Folders First`：

> **不生效。**

Pinned 文件与文件夹：

> 永远按照用户手工拖拽顺序混排。

例如：

```text
★ README.md
★ src/
★ architecture.md
★ docs/
```

这是合法顺序。

---

### Unpinned Area

`Folders First`：

> 正常生效。

如果开启：

```text
docs/
tests/
config.yaml
main.py
```

如果关闭：

> 所有 Unpinned Item 按统一名称规则排序。

因此：

> Pinned 是“人工优先级”；Unpinned 是“自动排序”。

---

# 37. Pin 支持文件和文件夹

例如：

```text
★ README.md
★ architecture.md
★ src/

AGENTS.md
config.yaml
docs/
tests/
```

文件和文件夹均可 Pin。

---

# 38. Pin 只能作用于相同父目录

例如：

```text
docs/
├─ api.md
├─ design.md
└─ database.md
```

Pin：

```text
design.md
```

变成：

```text
docs/
├─ ★ design.md
├─ api.md
└─ database.md
```

不能把它视觉上提升到 Project Root。

Pin：

> 只改变 sibling display order。

绝不改变真实文件路径。

---

# 39. Pinned Area 手工排序

Pinned Items 支持拖拽。

文件与文件夹允许混排。

例如：

```text
★ architecture.md
★ README.md
★ src/
★ config.yaml
```

可以拖成：

```text
★ README.md
★ config.yaml
★ architecture.md
★ src/
```

只改变：

> 当前 Parent 下 Pinned Items 的显示顺序。

---

# 40. 新文件规则

Agent 新创建的文件或文件夹：

> 默认属于 Unpinned。

自动进入 Unpinned Area，并按照当前自动排序规则显示。

这样不存在：

> 新文件在 Manual Order 中应该插到哪里？

的问题。

---

# 41. Pin Rename

如果可靠识别：

```text
design.md
→ architecture.md
```

则同步更新：

- File Tab；
- relativePath；
- Pin Record；

并保持原 Pin 位置。

---

# 42. Pin Delete

Pinned 文件被删除：

> 自动清理 Pin Record。

---

# 43. Git Review UI 总原则

Git UI：

> **高度参考 VS Code Source Control View 的信息架构和交互模型。**

目标：

> 熟悉 VS Code 的用户几乎无需重新学习。

但 AI Project Viewer 只做：

# Git Review

不做 Git Mutation。

---

# 44. Git Panel 保留内容

参考 VS Code 保留：

- Changed File Badge；
- Branch；
- Ahead / Behind；
- Changes；
- Staged Changes；
- 点击文件查看 Diff；
- Recent Commits。

---

# 45. Git Panel 删除的操作

V1 不提供：

- Stage；
- Unstage；
- Commit Message；
- Commit；
- Discard；
- Push；
- Pull；
- Sync；
- Branch Management；
- Merge；
- Rebase。

---

# 46. Git 三层信息结构

## 第一层：Project Tab

```text
QuantSystem ●
GewuCode ✓
```

表示：

> 当前 Project Scope Clean / Dirty。

---

## 第二层：Git Badge

```text
Git [7]
```

表示：

> 当前 Project Scope Changed File Unique Count。

---

## 第三层：File Tree

具体文件：

```text
M strategy.py
A risk.py
? notes.md
```

---

# 47. 文件夹不显示 Git 聚合 Count

V1 不显示：

```text
src [5]
docs [2]
```

避免信息噪声。

---

# 48. 文件夹不显示 Git 聚合状态

不显示：

```text
M src/
```

Git 真正变化对象是文件。

---

# 49. 折叠目录 Blind Spot

这是：

# 已知且有意接受的 UX 取舍

例如：

```text
▸ src
```

里面实际存在：

```text
M strategy.py
```

折叠时：

> `src` 不强制显示 descendant Git indicator。

完整变化应通过：

```text
Git [N]
```

查看。

这是为了控制文件树视觉噪声，不属于 Bug。

Future 可评估：

```text
▸ src •
```

轻量提示。

V1 不实现。

---

# 50. Git Panel 结构

点击：

```text
Git [7]
```

Sidebar 内容切换为：

```text
Git

main ↑2 ↓0

CHANGES  5

M src/strategy.py
M docs/design.md
D old_config.py
? notes.md
? test.md


STAGED CHANGES  2

M config.yaml
A src/risk.py


RECENT COMMITS

a3248d Update strategy
91ca76 Fix loading
71bc22 Add risk model
```

---

# 51. Changes

表示：

> Working Tree 中尚未 Stage 的变化。

点击：

> 主 Viewer 打开 Working Tree Diff。

---

# 52. Staged Changes

表示：

> 已进入 Git Index 的变化。

点击：

> Viewer 打开 Staged Diff。

---

# 53. 同一文件允许同时存在两组

同一文件可能：

```text
STAGED CHANGES
M config.yaml
```

同时：

```text
CHANGES
M config.yaml
```

不得错误去重。

但 Git Badge：

> Unique Path Count，只计算一次。

---

# 54. Recent Commits

默认显示最近：

```text
20
```

条。

至少包含：

- Short Hash；
- Commit Message；
- Relative Time。

**可点击**(2026-10-10 owner 验收增量)：每条提交可点击,点击后在查看区打开
**提交详情视图**——含完整 Message、作者、日期、Hash,以及该提交涉及的项目内
文件列表(文件可再点击,进入该提交视角下的该文件 diff)。样式对齐 VS Code
Source Control/Graph 的信息层级。

例如：

```text
a3248d  Update strategy       2h ago
91ca76  Fix loading           yesterday
```

---

# 55. Git Root 检测

每个 Project 的 Git 状态不能简单假定：

> Project Root == Git Root。

Git Refresh 时必须确定：

```text
Project Root
↓
git rev-parse --show-toplevel
↓
Git Root
```

---

# 56. Git 场景 A：Project Root = Git Root

例如：

```text
D:\Projects\QuantSystem
```

也是：

```text
Git Root
```

采用正常 Repository View。

所有：

- Badge；
- Changes；
- Staged；
- Recent Commits；
- File Marks；

覆盖整个 Repository。

---

# 57. Git 场景 B：Project Root 位于更大的 Git Repository 内部

例如用户添加：

```text
D:\Projects\BigRepo\apps\viewer
```

但：

```text
Git Root =
D:\Projects\BigRepo
```

则 AI Project Viewer 采用：

# Repository-aware, Project-scoped

原则：

> **Git identity is repository-wide; Git change presentation is project-scoped.**

---

# 58. Git 子目录模式 UI

Git Panel 顶部增加轻量说明：

```text
main ↑2 ↓1

Repository: BigRepo
Scope: apps/viewer
```

明确告诉用户：

> 当前 Project 是更大 Git Repository 的一个子目录。

---

# 59. Git 子目录模式 Badge

```text
Git [7]
```

只统计：

> 当前 Project Scope 内发生变化的唯一文件路径。

父 Repository 中：

```text
apps/backend
packages/common
```

等其他区域的 Changes：

> 不计入当前 Project Badge。

---

# 60. Git 子目录模式 Project Tab

Project Tab 的：

```text
✓ / ●
```

也只代表：

> 当前 Project Scope Clean / Dirty。

不是整个父 Repository 的 Dirty State。

---

# 61. Git 子目录模式 Changes

Git Panel 中：

```text
CHANGES
STAGED CHANGES
```

只显示当前 Project Scope 下的文件。

例如 Scope：

```text
apps/viewer
```

则只显示：

```text
apps/viewer/...
```

的 Git Changes。

---

# 62. Git 子目录模式 File Tree Marks

Files Tree 只能显示：

> 当前 Project Scope 能映射到的文件变化。

父 Repo 其他目录变化：

> 不显示。

---

# 63. Git 子目录模式 Branch / Ahead / Behind

以下信息仍然是：

> Repository-wide。

因此：

```text
main ↑2 ↓1
```

仍然显示父 Repository 的 Branch 和 Ahead / Behind。

因为这些不是目录级属性。

---

# 64. Git 子目录模式 Recent Commits

Recent Commits：

> 默认只显示影响当前 Project Scope 的最近 Commit。

避免父 Repository 中与当前项目无关的 Commit 淹没信息。

---

# 65. Git 子目录 Path 映射

Git CLI 的返回基准**不统一**（2026-10-10 合入定稿附注 A 的事实性修正）：

> `git status --porcelain` 在子目录运行时，输出相对**当前工作目录**的路径；
> `git diff` / `git log` 输出相对 **Git Root** 的路径。

因此规约：

> 所有 Git 命令统一以 `git -C <GitRoot>` 方式执行。

这样全部输出统一相对 Git Root，再统一进行 Scope 过滤与 Project-relative 换算。

应用必须安全转换为：

> Project-relative Path。

用于：

- File Tree；
- Badge；
- Diff；
- Tab；
- Git Panel。

---

# 66. Project Root 不属于任何 Git Repository

如果：

```text
git rev-parse --show-toplevel
```

失败：

> 视为 Non-Git Project。

V1 不递归扫描 Project 内部是否包含多个 Nested Repositories。

例如：

```text
Projects/
├─ AppA/.git
└─ AppB/.git
```

如果用户把：

```text
Projects/
```

本身作为 Project 加入：

> V1 将其视为 Non-Git Project。

用户如需 Git Review：

> 应分别添加 AppA / AppB。

这避免引入 Multi-Repository Workspace 复杂度。

---

# 67. Ahead / Behind

例如：

```text
main ↑2 ↓1
```

表示：

```text
↑2
本地 Branch 比 Upstream 多 2 个 Commit

↓1
Upstream 比本地多 1 个 Commit
```

没有 Upstream：

> 不显示 ↑↓。

---

# 68. Git Engine

使用：

```text
System Git CLI
```

不内嵌完整 Git Engine。

---

# 69. Git Status

使用类似：

```text
git status --porcelain=v2 --branch
```

解析：

- Branch；
- Upstream；
- Ahead；
- Behind；
- Modified；
- Added；
- Deleted；
- Renamed；
- Untracked；
- Staged；
- Unstaged；
- Conflict。

---

# 70. Git Safe Review Mode

Git Review 不应因为 Repository 配置触发用户未主动请求的外部程序。

Diff 至少采用：

```text
--no-pager
-c core.quotepath=false
--no-ext-diff
--no-textconv
```

目标：

- 禁用 Pager；
- 中文文件名正常；
- 禁止 External Diff Driver；
- 禁止 Textconv External Program。

---

# 71. Git Diff

V1 使用：

# Unified Diff

支持：

- Added；
- Deleted；
- Context；
- Working Tree Diff；
- Staged Diff。

Diff 呈现方式为 **Side-by-side(并排双栏)**(2026-10-10 owner 验收提前,
原定 P1):左右双栏各带行号与路径列头,删除行红底/新增行绿底,单侧变更的
对侧留空,未变化区段折叠为"⋯ N unchanged lines"计数条。Unified 格式仍是
内部解析输入,不再作为呈现方式。

# 72. Git Diff Size Guard

Backend 限制：

```text
max bytes
+
max lines
```

建议初始：

```text
2 MB
或
20,000 lines
```

任一达到则停止继续发送。

UI：

```text
Diff is too large to display.

[Open in VS Code]
```

---

# 73. Git Refresh：Phase 7

Phase 7 尚未实现 Watcher。

只要求：

```text
Project Open
Project Switch In
Window Regain Focus
Manual Refresh
```

---

# 74. Git Refresh：Phase 9

Watcher 完成后增加：

```text
Agent changes file
↓
Watcher
↓
Debounce
↓
Git Refresh
```

---

# 75. Git Debounce

推荐：

```text
约 400 ms
```

允许根据 Benchmark 调整：

```text
300–500 ms
```

---

# 76. Watcher

Watcher：

> 文件变化监听器。

作用：

```text
Agent 修改 architecture.md
↓
Watcher 发现变化
↓
Viewer Refresh
↓
Git Refresh
```

---

# 77. Active / Inactive Project Watch

默认：

```text
Active Project
→ Real-time Watch
```

Inactive Project：

```text
→ 不维持 Full Real-time Watch
```

目的：

> 降低 CPU、Handle、后台事件和 Git 开销。

---

# 78. Inactive Project Git 更新

切换到该项目：

> 立即刷新 Git。

窗口重新获得 Focus：

> 可以低成本刷新 Summary。

如果 Benchmark 表明多项目刷新明显有负担：

> 只刷新 Active Project。

---

# 79. Watcher 与 Tree Expansion 解耦

禁止：

```text
Folder collapsed
→ 不 Watch
```

Agent 可以修改任何正常源码目录。

File Tree 展开状态：

> 不决定 Watcher 语义。

---

# 80. Watcher Ignore

默认尽量忽略：

```text
.git
node_modules
.venv
venv
__pycache__
.cache
.next
coverage
dist
build
target
```

实现必须尽可能减少 Event Storm。

但不能漏掉正常项目源码变化。

---

# 81. Watcher Debounce

推荐：

```text
300–500ms
```

连续：

```text
write
rename
write
save
```

合并为一次逻辑 Refresh。

---

# 82. 当前文件被 Agent 更新

如果当前打开文件发生外部修改：

> 自动重新读取。

显示：

```text
✓ architecture.md updated
```

轻量 Toast。

约 1–2 秒后消失。

连续更新：

> Debounce 后只显示一次。

---

# 83. 当前文件被删除

如果 Agent 删除当前 Tab 文件：

Tab：

> 暂时保留。

Viewer：

```text
architecture.md

This file has been deleted.

[Close Tab]
```

不得：

- Crash；
- 无提示关闭 Tab。

---

# 84. 当前文件 Rename

可靠识别：

```text
design.md
→ architecture.md
```

同步更新：

- Tab Title；
- FileTabState.relativePath；
- Active File；
- Pin Record。

---

# 85. 无法确认 Rename

按照：

```text
Old File Deleted
+
New File Added
```

处理。

旧 Tab：

```text
This file has been deleted.
```

新文件：

> 正常进入 Tree。

---

# 86. Markdown Viewer

`.md/.markdown`

默认：

# Rendered

不是 Source。

右上：

```text
Rendered | Source
```

Source：

> Read-only。

---

# 87. Markdown V1 能力

支持：

- Heading；
- Bold；
- Italic；
- Ordered List；
- Unordered List；
- Task List；
- Table；
- Blockquote；
- Inline Code；
- Code Block；
- Syntax Highlight；
- Local Image；
- Link；
- Horizontal Rule；
- GitHub Flavored Markdown。

推荐：

```text
markdown-it
```

---

# 88. Markdown Security

Raw HTML：

> 默认禁用，

或经过严格 Sanitization。

禁止任意 JavaScript / Script 执行。

---

# 89. Markdown Local Link

项目内部：

```text
./architecture.md
```

→ 当前应用中打开。

HTTP / HTTPS：

→ Default Browser。

---

# 90. Mermaid

# P1

不能阻塞 V1。

Markdown 架构需允许后续添加 Renderer Extension。

---

# 91. PDF

PDF：

# P0

正式采用：

# PDF.js

不再比较 WebView2 Native PDF。

---

# 92. PDF Viewer V1

必须支持：

- Previous Page；
- Next Page；
- Current Page / Total Pages；
- Page Jump；
- Zoom In；
- Zoom Out；
- Fit Width；
- Fit Page；
- Ctrl + Mouse Wheel Zoom；
- Text Search；
- Scroll。

---

# 93. PDF State

切离 PDF 保存：

- Page；
- Zoom；
- Scroll Position。

返回：

> 恢复。

---

# 94. PDF Lazy Load

未打开 PDF：

> 不主动初始化完整 PDF Viewer。

第一次打开：

> 才加载相关模块。

---

# 95. PDF Virtualization

禁止一次 Render：

```text
200 pages
```

只保留：

```text
Visible Pages
+
少量 Adjacent Pages
```

具体缓存范围通过 Benchmark 调整。

---

# 96. Inactive PDF Release

切离 PDF 后：

尽量释放：

- Canvas；
- Render Task；
- Page Cache；
- PDF Document；
- Worker 可释放资源。

只保存轻量 State。

---

# 97. PDF Technical Spike

Phase 5 首先验证：

- Tauri Asset Protocol；
- assetScope；
- Local PDF Access；
- PDF.js Worker；
- CSP `worker-src`；
- CSP `img-src`；
- Markdown Local Image；
- Worker Lifecycle。

优先：

```text
Load Local PDF
↓
Worker Works
↓
Render One Page
↓
再开发完整 UI
```

---

# 98. PDF Benchmark

至少测试：

### A

10 页文本 PDF。

### B

100 页文本 PDF。

### C

100 页扫描 PDF。

### D

5 个 PDF Tabs，仅 1 个 Active。

记录：

- Before Open RAM；
- After Open RAM；
- Deep Scroll RAM；
- Switch Away RAM；
- Close RAM。

---

# 99. PDF Future

Future / Evaluate：

- PDF TOC；
- PDF Thumbnail Sidebar；
- PDF Annotation。

不进入 V1。

---

# 100. Text Viewer

支持：

```text
.txt
.log
.csv
```

至少：

- Selection；
- Copy；
- Ctrl+F；
- Scroll。

---

# 101. 文件检测流水线

Rust Backend 固定顺序：

```text
1. stat()
↓
2. file size guard
↓
3. BOM detection
↓
4. binary detection
↓
5. UTF-8 strict decode
↓
6. GB18030 fallback
```

---

# 102. BOM

支持：

- UTF-8 BOM；
- UTF-16 LE BOM；
- UTF-16 BE BOM。

BOM 必须先于 Binary NULL Detection。

---

# 103. 无 BOM UTF-16

V1 不强求智能检测。

被判成 Binary：

> 属于已知可接受限制。

---

# 104. Binary Detection

未知文件：

读取少量头部：

```text
4–16 KB
```

检测：

- NULL；
- Binary characteristics。

Binary Detect：

> 必须在 GB18030 Fallback 之前。

---

# 105. Encoding

支持：

```text
UTF-8
UTF-8 BOM
UTF-16 LE BOM
UTF-16 BE BOM
GB18030 fallback
```

状态栏：

```text
UTF-8
```

或：

```text
GB18030
```

Manual Encoding Override：

# P1

---

# 106. Large File Guard

Rust 先：

```text
stat()
```

再读取。

建议：

### `<5 MB`

正常打开。

### `5–20 MB`

提示：

```text
Large file.

Opening this file may affect performance.

[Open Anyway]
```

### `>20 MB`

默认不整体发送到 WebView。

提供：

```text
Show in File Explorer
Open with System Default App
```

PDF 使用独立规则。

---

# 107. Code Viewer

至少支持：

```text
.py
.js
.ts
.tsx
.jsx
.rs
.go
.java
.c
.cpp
.h
.html
.htm
.css
.scss
.json
.yaml
.yml
.toml
.sh
.ps1
.cmd
.bat
.sql
```

推荐：

```text
CodeMirror 6
```

Minimal Read-only。

功能：

- Syntax Highlight；
- Line Number；
- Ctrl+F；
- Copy；
- Jump to Line；
- Scroll。

---

# 108. JSON / YAML / TOML

### JSON

默认：

```text
Formatted JSON Viewer
```

可切：

```text
Source
```

### YAML / YML

```text
Code Viewer
```

### TOML

```text
Code Viewer
```

---

# 109. Image Viewer

支持：

- PNG；
- JPG；
- JPEG；
- WebP；
- GIF；
- SVG。

功能：

- Fit；
- Actual Size；
- Zoom；
- Pan。

---

# 110. SVG Security

SVG 必须使用：

> Safe Image Context。

例如：

```html
<img>
```

禁止：

- `innerHTML`；
- `iframe`；
- `object`；
- `embed`。

避免 SVG Script 执行。

---

# 111. HTML

`.html/.htm`

左键：

> Code Viewer。

右键：

```text
Open in Browser
```

---

# 112. HTML file:// 边界

普通静态 HTML：

> 可以调用 Default Browser。

V1 不保证以下源码项目通过 `file://` 正常运行：

- Vite；
- React；
- Vue；
- Next；
- ES Module App；
- SSR App。

---

# 113. 现代 Web Project

推荐：

```text
Run project start script
↓
Dev Server
↓
localhost
↓
Browser
```

本应用：

> 不承担 Build Tool / Dev Server。

P1 可增加：

```text
Project Web URL
```

例如：

```text
http://localhost:5173
```

---

# 114. Serve Static Folder

# P1

仅针对已经完成 Build 的静态产物：

```text
dist/
build/
```

不作为通用 Framework Dev Server。

---

# 115. `.url`

左键：

> URL Info Viewer。

右键：

```text
Open in Browser
```

自动打开只允许：

```text
http:
https:
```

禁止：

```text
javascript:
powershell:
cmd:
file:
shell:
```

---

# 116. Script RUN

V1 支持：

```text
.ps1
.cmd
.bat
```

左键：

> Code Viewer。

绝不因为单击或双击直接执行。

---

# 117. Script Run Console

脚本必须：

> 在独立、可见的外部 Console 中运行。

例如：

```text
AI Project Viewer
↓
Run start.ps1
↓
Visible PowerShell Console
↓
stdout / stderr visible
```

禁止后台静默运行。

---

# 118. Script Console 实现要求

需求规定的是：

> 最终可见行为。

不能依赖：

> “只要不 Redirect stdio，Windows 就一定出现 Console”

这种假设。

实现层必须显式确保：

- Console 可见；
- stdout/stderr 可见；
- 快速结束脚本的结果仍有机会阅读。

具体 Windows 进程创建策略由 Phase 8 验证决定。

---

# 119. Run 反馈

(2026-10-11 owner 修订)Launch **Success:无提示**——弹出的可见
Console/程序窗口本身就是反馈,不再显示任何横幅。

Launch **Failure:窗口正中的醒目错误弹窗**,标题为
`Failed to launch start.ps1`,正文写明具体错误原因(如路径不存在),
一眼可见;关闭方式=OK 按钮或 Esc。

Toast 不能替代 Console。

---

# 120. PowerShell

`.ps1`：

> 遵守系统 ExecutionPolicy。

禁止自动：

```text
-ExecutionPolicy Bypass
```

---

# 121. Script Working Directory

`.ps1/.cmd/.bat`

默认：

```text
cwd = Project Root
```

P1：

```text
Run from Script Directory
```

---

# 122. EXE

`.exe`

左键：

> Executable Info Viewer。

例如：

```text
tool.exe

Windows Executable

Size:
Modified:
Path:

This file cannot be previewed.
```

---

# 123. EXE Run

右键：

```text
Run
```

使用：

> Absolute EXE Path。

不得通过：

```text
cmd /c
```

字符串拼接启动。

---

# 124. EXE Working Directory

默认：

```text
cwd = EXE Parent Directory
```

---

# 125. Run as Administrator

# P1

---

# 126. MSI

`.msi`

左键：

# Unsupported Viewer

右键允许：

```text
Open with System Default App
Show in File Explorer
Copy Absolute Path
Copy Relative Path
```

不提供普通：

```text
Run
```

---

# 127. Python / JS / SH 不直接 RUN

V1 不提供：

```text
Run Python
Run JavaScript
Run Shell
```

避免引入：

- Interpreter Discovery；
- venv；
- Conda；
- uv；
- Node；
- Bun；
- Deno；
- WSL；
- Git Bash。

---

# 128. Project Trust

新项目默认：

```text
Untrusted for Execution
```

第一次运行：

```text
.ps1
.cmd
.bat
.exe
```

显示：

```text
This project contains executable files.

Running scripts or programs can modify files or your system.

[Trust and Run]
[Cancel]
```

---

# 129. Trust

Trust：

- 可持久化；
- 可撤销；
- 不跨项目继承。

Project Context Menu：

```text
Trust Project for Execution
```

或：

```text
Untrust Project
```

---

# 130. Quick Edit：Notepad

Text-like 文件：

右键：

```text
Edit in Notepad
```

适合：

- 配置修改；
- Markdown 小改；
- TXT；
- JSON；
- `.env`；
- 少量脚本修改。

---

# 131. Full Edit：VS Code

右键：

```text
Open in VS Code
```

用于：

- 正式代码修改；
- 多文件修改；
- Refactor；
- Debug。

---

# 132. External Editor Backend Abstraction

Rust 内部保留轻量 Editor 抽象。

概念：

```typescript
interface ExternalEditor {
  id: string
  name: string

  openFile(path: string): Result

  openFolder?(path: string): Result
}
```

V1：

```text
NotepadEditor
VSCodeEditor
```

未来可扩展：

- Notepad++；
- Cursor；
- Zed；
- PyCharm；
- Custom Editor。

不因此建立插件系统。

---

# 133. 前端执行安全边界

Frontend 不允许拥有：

```text
run_arbitrary_executable()
```

之类通用执行能力。

只提供语义化命令：

```text
edit_in_quick_editor
open_in_code_editor
run_project_script
run_project_executable
```

真正的 Executable / Args / Path Validation：

> 由 Rust Backend 控制。

---

# 134. VS Code Mode

Settings：

```text
Open in VS Code

● New Window
○ Reuse Existing Window
```

默认：

```text
New Window
```

---

# 135. File Context Menu：Text-like

```text
Open

────────────────

Edit in Notepad
Open in VS Code

────────────────

Show in File Explorer

Copy Absolute Path
Copy Relative Path

────────────────

Pin to Top / Unpin
```

---

# 136. HTML Context Menu

```text
Open

────────────────

Open in Browser

────────────────

Edit in Notepad
Open in VS Code

────────────────

Show in File Explorer
Copy Absolute Path
Copy Relative Path

────────────────

Pin to Top / Unpin
```

---

# 137. Script Context Menu

```text
Open

────────────────

Run Script

────────────────

Edit in Notepad
Open in VS Code

────────────────

Show in File Explorer
Copy Absolute Path
Copy Relative Path

────────────────

Pin to Top / Unpin
```

---

# 138. PDF Context Menu

```text
Open

────────────────

Open with Default PDF App

────────────────

Show in File Explorer
Copy Absolute Path
Copy Relative Path

────────────────

Pin to Top / Unpin
```

---

# 139. EXE Context Menu

```text
Run

────────────────

Show in File Explorer
Copy Absolute Path
Copy Relative Path

────────────────

Pin to Top / Unpin
```

---

# 140. Folder Context Menu

```text
Open

────────────────

Show in File Explorer

Copy Absolute Path
Copy Relative Path

────────────────

Open Folder in VS Code

────────────────

Pin to Top / Unpin
```

---

# 141. Project Context Menu

```text
Open in File Explorer

Copy Project Path

Open Project in VS Code

────────────────

Refresh Project

Trust / Untrust Project for Execution

────────────────

Remove Project
```

---

# 142. 文件类型行为总表

| 文件类型 | 左键行为 | 特殊 / RUN | Quick Edit | Full Edit |
|---|---|---|---|---|
| `.md` | Rendered Markdown | Source Toggle | Notepad | VS Code |
| `.txt/.log/.csv` | Text Viewer | — | Notepad | VS Code |
| `.py/.js/.ts/...` | Code Viewer | — | Notepad | VS Code |
| `.json` | Formatted JSON | Source Toggle | Notepad | VS Code |
| `.yaml/.yml` | Code Viewer | — | Notepad | VS Code |
| `.toml` | Code Viewer | — | Notepad | VS Code |
| `.pdf` | PDF Viewer | Default PDF App | — | — |
| PNG/JPG/WebP/GIF/SVG | Image Viewer | System App | — | — |
| `.html/.htm` | Code Viewer | Open in Browser | Notepad | VS Code |
| `.url` | URL Info | Open in Browser | Notepad | VS Code |
| `.ps1` | Code Viewer | Run Script | Notepad | VS Code |
| `.cmd/.bat` | Code Viewer | Run Script | Notepad | VS Code |
| `.exe` | Executable Info | Run | — | — |
| `.msi` | Unsupported Viewer | System Default | — | — |
| Text-like Unknown | Text Viewer | — | Notepad | VS Code |
| Binary Unknown | Unsupported Viewer | System Default | — | — |

此表：

> 是 File Action Resolver 的权威规格。

---

# 143. Path Security

所有：

- Read；
- Run；
- Reveal；
- Open；

执行前均需安全验证。

---

# 144. Windows Canonicalization

禁止：

```text
rawTarget.startsWith(rawRoot)
```

这种字符串安全判断。

需要：

```text
canonical PathBuf
+
normalized path
+
Path semantic starts_with
```

并正确处理 Windows：

```text
\\?\
```

Extended Path Prefix。

---

# 145. Command Security

任何：

- Git；
- PowerShell；
- CMD；
- EXE；

调用必须采用：

```text
Executable
+
Argument Array
```

禁止 Shell String 拼接。

---

# 146. 核心快捷键

V1/P0：

```text
Ctrl + W
Close Current File Tab

Ctrl + F
Find in Current Viewer

Ctrl + Tab
Next File Tab

Ctrl + Shift + Tab
Previous File Tab

Ctrl + R
Refresh Active Project
```

---

# 147. WebView2 快捷键冲突

Application Shortcut：

> 必须优先于 WebView2 自带浏览器 Accelerator 行为。

必须处理例如：

```text
Ctrl+F
Ctrl+R
Ctrl+P（P1）
Ctrl+W
```

等潜在冲突。

实现可以采用：

- 禁用冲突的 WebView2 Browser Accelerator；
- 或在应用层显式 Intercept。

目标：

```text
Ctrl+R
```

必须执行：

> Refresh Active Project，

不能变成：

> Reload WebView 页面。

该要求进入正式验收。

---

# 148. Ctrl+P

# P1

作用：

> Quick Open / 按文件名搜索项目文件。

---

# 149. Ctrl+P 实现

不强制建立常驻 File Index。

可采用：

```text
Ctrl+P
↓
On-demand Async Enumeration
↓
Apply Ignore Rules
↓
Temporary File List
↓
Fuzzy Search
```

可进行短期缓存。

不允许因此让 V1 启动时递归扫描整个项目。

---

# 150. Search Sidebar

全文 Search：

# P1

未来：

```text
Files   Git [N]   Search                    ⚙
```

Search：

> 搜索项目文件内容。

---

# 151. Empty State

第一次启动：

```text
AI Project Viewer

Open your first project

[ Open Folder ]

Read.
Review.
Run.
Hand off.
```

---

# 152. Non-Git Project

项目没有 `.git`，且不处于父 Git Repository 内：

仍完整支持：

```text
READ
RUN
HANDOFF
```

Git Panel：

```text
This folder is not a Git repository.
```

不得影响 Project Open。

---

# 153. Git 未安装

如果：

```text
git.exe
```

不可用：

```text
Git is not installed or cannot be found.

Git review is unavailable.

File browsing remains available.
```

不得阻止应用使用。

---

# 154. Theme

支持：

```text
System
Dark
Light
```

默认：

```text
System
```

---

# 155. UX 风格

定位：

> Developer Tool。

要求：

- Compact；
- Functional；
- Fast；
- Clear；
- 中高信息密度。

避免：

- Marketing Dashboard；
- 巨大 Card；
- 夸张圆角；
- 过量动画；
- 大面积无意义留白。

---

# 156. 推荐技术栈

```text
Tauri 2
Rust

Svelte
TypeScript
Vite

markdown-it

CodeMirror 6

PDF.js

System Git CLI

JSON State
```

---

# 157. Backend 建议结构

```text
src-tauri/
│
├─ project/
│  ├─ project_manager.rs
│  └─ project_session.rs
│
├─ fs/
│  ├─ directory.rs
│  ├─ reader.rs
│  ├─ inspect.rs
│  ├─ encoding.rs
│  ├─ binary_detect.rs
│  └─ watcher.rs
│
├─ git/
│  ├─ command.rs
│  ├─ repository.rs
│  ├─ status.rs
│  ├─ diff.rs
│  └─ log.rs
│
├─ runner/
│  ├─ browser.rs
│  ├─ script.rs
│  └─ executable.rs
│
├─ external/
│  ├─ editor.rs
│  ├─ notepad.rs
│  ├─ vscode.rs
│  └─ explorer.rs
│
├─ security/
│  ├─ path.rs
│  ├─ url.rs
│  └─ project_trust.rs
│
├─ state/
│  ├─ migration.rs
│  └─ persistence.rs
│
└─ main.rs
```

---

# 158. Frontend 建议结构

```text
src/
│
├─ components/
│  ├─ ProjectTabs/
│  ├─ SidebarHeader/
│  ├─ FileTabs/
│  ├─ FileTree/
│  ├─ GitPanel/
│  ├─ ContextMenu/
│  ├─ RunConfirmation/
│  └─ StatusBar/
│
├─ viewers/
│  ├─ MarkdownViewer/
│  ├─ PdfViewer/
│  ├─ TextViewer/
│  ├─ CodeViewer/
│  ├─ JsonViewer/
│  ├─ ImageViewer/
│  ├─ DiffViewer/
│  ├─ UrlViewer/
│  └─ UnsupportedViewer/
│
├─ stores/
│  ├─ projectStore.ts
│  ├─ fileTreeStore.ts
│  ├─ tabsStore.ts
│  ├─ runtimeGitStore.ts
│  ├─ trustStore.ts
│  └─ settingsStore.ts
│
└─ services/
```

---

# 159. 推荐 Tauri Commands

至少：

```text
select_project_directory

list_directory

inspect_file

read_text_file

reveal_in_explorer

open_system_default

edit_in_quick_editor

open_in_code_editor

open_folder_in_code_editor

open_project_in_code_editor

open_in_browser

run_powershell_script

run_cmd_script

run_executable

git_repository_info

git_status

git_diff

git_staged_diff

git_log

start_active_project_watcher

stop_active_project_watcher

get_project_trust

set_project_trust
```

---

# 160. 性能原则

必须执行：

1. Lazy File Tree；
2. Tree Visibility 与 Watcher Ignore 分离；
3. 不做 Full Manual Sort；
4. Pinned Items 只存用户主动关注的节点；
5. Inactive Viewer Unmount；
6. PDF Lazy Load；
7. PDF Page Virtualization；
8. Inactive PDF Release；
9. Rust-side Large File Guard；
10. Rust-side Binary Detection；
11. Active Project Watch Only；
12. Watcher Debounce；
13. Git Debounce；
14. Git Diff Size Guard；
15. 无后台高频 Polling；
16. 不内置 Browser；
17. 不内置 Terminal；
18. 不维护 V1 全项目常驻 File Index。

---

# 161. 内存统计口径

必须统计：

# 整个 Process Tree

包括：

```text
AI Project Viewer Rust Process
+
msedgewebview2.exe
+
Worker / Helper
```

不能只统计 Main EXE。

---

# 162. Phase 1 Baseline

Phase 1 完成立即记录：

- Startup Time；
- Idle Process-tree RAM；
- Idle CPU；
- WebView2 Process Count。

作为：

> Baseline。

---

# 163. 内存目标

绝对值：

```text
≤150 MB
```

只是：

> Target。

不是硬性 Release Gate。

更重要：

> 相同真实场景明显低于 VS Code。

参考：

```text
约 ≤ VS Code RAM 50%
```

最终以实际 Benchmark 为准。

---

# 164. Cold Start

目标：

```text
≤2 seconds
```

进入主窗口。

受首次 WebView2 初始化影响时：

> 记录真实结果。

---

# 165. Idle CPU

没有：

- 用户操作；
- Watch Event；
- Git Refresh；
- PDF Render；

时：

> CPU 接近 Idle。

---

# 166. Benchmark A：Shell

```text
0 Projects
```

测：

- Startup；
- RAM；
- CPU。

---

# 167. Benchmark B：Normal Project

```text
1 Project

5 Markdown
3 Python
2 JSON
```

测：

- RAM；
- File Switch。

---

# 168. Benchmark C：Multi Project

```text
4 Projects

约 10 Tabs / Project

Only 1 Active Viewer
```

测：

- RAM；
- Project Switching；
- Session Restore。

---

# 169. Benchmark D：Large Project

存在：

```text
node_modules >100,000 files
```

确认：

- 启动不递归扫描；
- Tree Lazy；
- Watcher 不被 Event Storm 拖垮。

---

# 170. Benchmark E：Agent Changes

Agent 连续修改：

```text
10 Files
```

确认：

- UI 不冻结；
- Watcher Debounce；
- Git Debounce；
- Git 状态正确；
- 不产生大量 Git Processes。

---

# 171. Benchmark F：PDF

测试：

- 10-page PDF；
- 100-page PDF；
- 100-page Scan。

记录：

- Before；
- Open；
- Deep Scroll；
- Switch Away；
- Close。

---

# 172. Benchmark G：Multiple PDF Tabs

```text
5 PDF Tabs
1 Active
```

与：

```text
1 PDF Tab
```

比较。

Inactive PDF：

> 不应导致 RAM 线性上涨。

---

# 173. Benchmark H：Large Diff

构造：

```text
>20,000-line Diff
```

确认：

- Backend 截断；
- WebView 不接收完整巨大 Diff；
- UI 不冻结；
- 可以 Open in VS Code。

---

# 174. Benchmark I：Git Subdirectory Scope

构造：

```text
BigRepo/
├─ apps/viewer/      ← AI Project Viewer Project Root
├─ apps/backend/
└─ packages/
```

分别修改：

```text
apps/viewer/a.ts
apps/backend/b.ts
packages/c.ts
```

验收：

- Git Badge 只统计 viewer Scope；
- Project ● 只反映 viewer Scope；
- Changes 只显示 viewer Scope；
- Tree 只标 viewer Scope；
- Branch/Ahead/Behind 仍是 Repository-wide；
- Recent Commits 只显示影响 viewer Scope 的 Commit；
- UI 显示 Repository 与 Scope。

---

# 175. Phase 1 — Application Shell

只实现：

```text
Tauri 2
Svelte

Single Instance

Project Tabs

Add Project
Remove Project
Project Dedup

Sidebar Header:
Files
Git
Settings Entry
```

Settings：

> Placeholder / Theme Only。

同时处理：

> 应用级快捷键与 WebView2 Accelerator 基础冲突框架。

完成：

> Baseline Benchmark。

然后停止。

---

# 176. Phase 2 — File System & Favorites

实现：

```text
Lazy Tree

Tree Visibility

Show system/generated folders

Name Sort

Favorites First

Folders First 精确语义

Pin File
Pin Folder

Pinned Items Drag Order

Same-parent-only Pin

Project-relative Session Paths

inspect_file

Large File Guard

Binary Detection

Encoding Detection
```

重点：

> 排序永不改变真实文件路径。

---

# 177. Phase 3 — Basic READ

实现：

```text
File Tabs

Viewer Lifecycle

Markdown

Text

Code

JSON

Image

Secure SVG
```

同时完成：

```text
Ctrl+F
Ctrl+W
Ctrl+Tab
Ctrl+Shift+Tab
Ctrl+R
```

的完整应用级行为。

---

# 178. Phase 4 — Session & Settings

实现：

```text
AppState.version

ProjectSession

AppSettings

Pinned State Persistence

Expanded Folder Persistence

Debounced State Save

Atomic Replace

State Migration Skeleton

Session Restore

Settings UI
```

---

# 179. Phase 5 — PDF.js Spike

首先：

```text
Asset Protocol
assetScope
CSP

Local PDF

PDF Worker

Render First Page
```

随后：

```text
Virtualization

Search

Zoom

State Restore

Resource Release

Memory Benchmark
```

Spike 通过后再正式并入 Viewer。

---

# 180. Phase 6 — HANDOFF

实现：

```text
Show in Explorer

Copy Absolute Path
Copy Relative Path

Edit in Notepad

Open File in VS Code
Open Folder in VS Code
Open Project in VS Code

System Default App

Default PDF App

Browser
```

Backend：

> 保留 ExternalEditor 抽象。

Frontend：

> 不获得 Arbitrary Executable 权限。

---

# 181. Phase 7 — Git Review

实现：

```text
Git Repository Detection

Git Root / Project Scope

Git Subdirectory Scope

Git Sidebar Badge

Project Dirty / Clean Indicator

Git Panel patterned after VS Code Source Control

Branch
Ahead / Behind

Changes
Staged Changes

File Git Marks

Unified Diff
Staged Diff

Diff Limit

Scoped Recent Commits

Safe Git Command Layer
```

本阶段刷新：

```text
Project Open
Project Switch
Window Focus
Manual Refresh
```

---

# 182. Phase 8 — RUN / Trust

先完成：

```text
Project Trust
```

再：

```text
HTML → Browser
URL → Browser

PS1
CMD
BAT
EXE
```

脚本必须：

- Visible External Console；
- stdout/stderr 可见；
- 快速结束结果可读；
- Launch Success / Failure Toast。

---

# 183. Phase 9 — Watcher

实现：

```text
Active Project Watch

Watcher Ignore

Viewer Refresh

Git Refresh

Updated Toast

Delete Handling

Rename Handling

Pin Rename/Delete Synchronization

Watcher Debounce
```

注意：

```text
Tree Visibility
≠
Watcher Ignore
```

---

# 184. Phase 10 — Performance, Security & Release Preparation

本阶段禁止新增产品功能。

## Performance Review

检查：

- Event Listener Leak；
- CodeMirror Leak；
- PDF Worker Leak；
- Canvas Leak；
- Page Cache Leak；
- Watcher Leak；
- DOM Leak；
- Git Process Leak；
- Child Process Leak。

## Security Review

检查：

- Path Traversal；
- URL Scheme；
- SVG；
- Markdown Script；
- Git External Diff；
- Git Textconv；
- Command Injection；
- Project Trust；
- EXE Launch；
- Script Arguments；
- Frontend Shell Permission。

## Release Preparation

V1 发布前明确决定：

- Windows Installer Format；
- 是否 Code Sign；
- 是否 Auto Update。

初始建议：

```text
Development
→ tauri dev / local build

Personal-use V1 Release
→ NSIS-style Setup EXE

Auto Update
→ OFF

Code Signing
→ 非 V1 必需
```

如果未来公开分发：

> 再重新评估 Code Signing / Updater / MSI 等需求。

---

# 185. V1 P0

## Application

- Single Instance；
- Multi Project Tabs；
- Files/Git Sidebar Header；
- Settings；
- AppState Version；
- Session Restore；
- Atomic State Persistence。

## File Tree

- Lazy Tree；
- Tree Visibility；
- Show System Folders；
- Name Sort；
- Favorites First；
- Folders First；
- File Pin；
- Folder Pin；
- Pinned Manual Order；
- Project-relative UI State。

## READ

- Markdown；
- Text；
- Code；
- JSON；
- Image；
- PDF。

## REVIEW

- Project Scope Clean / Dirty；
- Git Badge；
- Git Root Detection；
- Subdirectory Scope；
- Branch；
- Ahead / Behind；
- Changes；
- Staged Changes；
- Git File Marks；
- Unified Diff；
- Scoped Recent Commits；
- Safe Git Review。

## RUN

- HTML；
- URL；
- PS1；
- CMD；
- BAT；
- EXE；
- Project Trust；
- Visible External Console。

## HANDOFF

- Notepad；
- VS Code；
- Explorer；
- Browser；
- System Default；
- Default PDF App；
- Copy Paths。

---

# 186. P1

- Search Sidebar；
- Ctrl+P Quick Open；
- Mermaid；
- Side-by-side Diff；
- Commit Detail；
- JSON Tree；
- Copy File Name；
- Copy Path for Prompt；
- Pin File Tab；
- Open With；
- Custom External Editor；
- Run as Administrator；
- Run from Script Directory；
- Project Web URL；
- Serve Built Static Folder；
- Encoding Manual Override；
- Recently Changed；
- Optional Live Monitor All Projects；
- Optional Collapsed-folder Git Descendant Indicator。

---

# 187. Future / Evaluate After V1

暂不承诺：

- Full Manual Sort；
- PDF TOC；
- PDF Thumbnail Sidebar；
- PDF Annotation；
- Full Git Graph；
- Python Runner；
- Node Runner；
- WSL Runner；
- Advanced Process Runner；
- Multi-Repository Workspace。

---

# 188. V1 工程验收 Checklist

## Application

- [ ] Single Instance 正常
- [ ] Project Tabs 正常
- [ ] Add Project 正常
- [ ] Remove Project 不删除真实目录
- [ ] Duplicate Project 被阻止
- [ ] AppState 包含 Version
- [ ] Session Restore 正常
- [ ] State Write 有 Debounce
- [ ] State 使用 Atomic Replace
- [ ] Settings Entry 正常

## Project Tabs

- [ ] Git Project Scope Clean 显示 ✓
- [ ] Git Project Scope Dirty 显示 ●
- [ ] Non-Git Project 不显示 Git 状态符号
- [ ] Inactive Project 可使用 Last Known State

## Path Persistence

- [ ] expandedFolders 使用项目相对路径
- [ ] Active File 使用相对路径身份
- [ ] File Tabs 使用 relativePath 恢复
- [ ] pinnedItems 使用相对路径
- [ ] 项目内部 UI 状态不无必要绑定盘符

## File Tree

- [ ] Lazy Load
- [ ] 启动不递归扫描完整项目
- [ ] `.git` 默认隐藏
- [ ] `node_modules` 默认隐藏
- [ ] `.venv` 默认隐藏
- [ ] `dist` 默认显示
- [ ] `build` 默认显示
- [ ] `target` 默认显示
- [ ] Show system/generated folders 可恢复隐藏目录
- [ ] Tree Visibility 与 Watcher Ignore 独立

## Favorites / Sorting

- [ ] Name Sort 正常
- [ ] Name Mode 的 Folders First 正常
- [ ] Favorites First 正常
- [ ] File 可 Pin
- [ ] Folder 可 Pin
- [ ] Pin 只作用于当前 Parent
- [ ] Pin 不改变真实路径
- [ ] Pinned Area 文件/文件夹可混排
- [ ] Pinned Area Drag Sort 正常
- [ ] Pinned Area 不受 Folders First 影响
- [ ] Unpinned Area 受 Folders First 控制
- [ ] Unpinned 新文件自动排序
- [ ] Rename 可靠识别时保留 Pin
- [ ] Delete 清理 Pin

## File Inspection

- [ ] stat 在完整读取前
- [ ] Size Guard 在 Rust 层
- [ ] BOM Detection 先于 Binary Detect
- [ ] Binary Detect 先于 GB18030
- [ ] UTF-8 Strict Decode
- [ ] GB18030 Fallback
- [ ] UTF-8 BOM
- [ ] UTF-16 LE BOM
- [ ] UTF-16 BE BOM
- [ ] Binary 不作为 Text 发送到 WebView
- [ ] Large File 不冻结 UI

## Markdown

- [ ] 默认 Rendered
- [ ] Source Toggle
- [ ] Source Read-only
- [ ] Table
- [ ] Task List
- [ ] Code Block
- [ ] Local Image
- [ ] Internal Link
- [ ] HTTP/HTTPS Link
- [ ] Raw Script 不执行

## Text / Code

- [ ] TXT
- [ ] LOG
- [ ] CSV
- [ ] Python Highlight
- [ ] JS/TS Highlight
- [ ] PS1 Highlight
- [ ] CMD/BAT 可查看
- [ ] Ctrl+F
- [ ] Read-only

## JSON / YAML / TOML

- [ ] JSON 默认 Formatted
- [ ] JSON 可切 Source
- [ ] YAML 使用 Code Viewer
- [ ] TOML 使用 Code Viewer

## Images

- [ ] PNG
- [ ] JPG/JPEG
- [ ] WebP
- [ ] GIF
- [ ] SVG
- [ ] SVG 使用 Safe Image Context
- [ ] SVG Script 不执行

## PDF

- [ ] PDF.js
- [ ] Local PDF Asset Protocol
- [ ] assetScope 正确
- [ ] CSP worker-src 正确
- [ ] CSP img-src 正确
- [ ] Previous / Next
- [ ] Page Jump
- [ ] Current / Total
- [ ] Zoom
- [ ] Fit Width
- [ ] Fit Page
- [ ] Ctrl+Wheel
- [ ] Search
- [ ] Page State Restore
- [ ] Virtualization
- [ ] Inactive PDF Release
- [ ] Worker Lifecycle
- [ ] 多 PDF Tab 不线性吃 RAM

## Git Availability

- [ ] Git Root = Project Root 正常
- [ ] Project 位于父 Git Repo 内正常
- [ ] Non-Git Project 正常
- [ ] git.exe Missing 不阻塞项目

## Git Subdirectory Scope

- [ ] 正确检测 Git Root
- [ ] 正确计算 Project Scope
- [ ] UI 显示 Repository
- [ ] UI 显示 Scope
- [ ] Badge 只统计 Scope 内 unique paths
- [ ] Project ●/✓ 只反映 Scope
- [ ] Changes 只显示 Scope
- [ ] Staged Changes 只显示 Scope
- [ ] File Marks 只显示 Scope
- [ ] Branch Repo-wide
- [ ] Ahead/Behind Repo-wide
- [ ] Recent Commits Scope-aware

## Git UI

- [ ] 信息结构接近 VS Code Source Control
- [ ] Badge 0 隐藏
- [ ] Badge 1–99
- [ ] Badge >=100 显示 99+
- [ ] 同文件 Staged+Unstaged 时 Badge 只计一次
- [ ] Folder 不显示 Git Count
- [ ] Folder 不显示聚合 M/A
- [ ] File M/A/D/R/?/U 正确
- [ ] Folded-folder Blind Spot 符合设计

## Git Status

- [ ] Branch
- [ ] Upstream
- [ ] Ahead
- [ ] Behind
- [ ] Modified
- [ ] Added
- [ ] Deleted
- [ ] Renamed
- [ ] Untracked
- [ ] Conflict
- [ ] Staged
- [ ] Unstaged
- [ ] 同文件允许同时出现在两组

## Git Diff

- [ ] Working Tree Diff
- [ ] Staged Diff
- [ ] Unified Diff
- [ ] Diff Size Guard
- [ ] Large Diff 不冻结
- [ ] Large Diff 可 Open VS Code
- [ ] no-pager
- [ ] core.quotepath=false
- [ ] no-ext-diff
- [ ] no-textconv
- [ ] 中文文件名正常

## Recent Commits

- [ ] Short Hash
- [ ] Message
- [ ] Relative Time
- [ ] Normal Repo 最近 Commit 正确
- [ ] Subdirectory Scope Commit 正确

## Watcher

- [ ] 默认只 Watch Active Project
- [ ] 与 Tree Expansion 无关
- [ ] Ignore 正常
- [ ] Watch Debounce
- [ ] Git Debounce
- [ ] Agent 修改当前文件自动刷新
- [ ] Updated Toast
- [ ] 连续保存不刷 Toast
- [ ] Delete 当前文件不 Crash
- [ ] Deleted State 正确
- [ ] Rename 更新 Tab
- [ ] Rename 更新 Pin

## HTML / URL

- [ ] HTML 左键源码
- [ ] HTML Open in Browser
- [ ] `.url` 正常
- [ ] URL 只允许 HTTP/HTTPS
- [ ] Modern Web file:// 边界明确

## Script RUN

- [ ] PS1
- [ ] CMD
- [ ] BAT
- [ ] 左键不运行
- [ ] Project Root cwd
- [ ] PowerShell 不 Bypass ExecutionPolicy
- [ ] Visible External Console
- [ ] stdout/stderr 可查看
- [ ] 快速结束不会无反馈闪退
- [ ] Launch Success Toast
- [ ] Launch Failure Toast

## EXE

- [ ] 左键不运行
- [ ] Executable Info Viewer
- [ ] Right-click Run
- [ ] Absolute Path Launch
- [ ] cwd = EXE Parent
- [ ] 不通过 cmd /c 拼接

## MSI

- [ ] Left Click = Unsupported Viewer
- [ ] 不显示普通 Run
- [ ] 可 System Default
- [ ] 可 Explorer

## Project Trust

- [ ] New Project Untrusted
- [ ] 首次 Script Run 确认
- [ ] 首次 EXE Run 确认
- [ ] Trust 持久化
- [ ] Trust 可撤销
- [ ] Trust 不跨项目

## HANDOFF

- [ ] Edit in Notepad
- [ ] Open File in VS Code
- [ ] Open Folder in VS Code
- [ ] Open Project in VS Code
- [ ] VS Code New Window 默认
- [ ] Explorer
- [ ] Copy Absolute Path
- [ ] Copy Relative Path
- [ ] System Default
- [ ] Default PDF Reader
- [ ] ExternalEditor 抽象
- [ ] Frontend 无 Arbitrary Executable 权限

## Keyboard

- [ ] Ctrl+W
- [ ] Ctrl+F
- [ ] Ctrl+Tab
- [ ] Ctrl+Shift+Tab
- [ ] Ctrl+R
- [ ] WebView2 不抢占上述 Application Shortcuts
- [ ] Ctrl+R 不 Reload 整个 WebView

## Empty / Error

- [ ] Empty State
- [ ] Git Missing
- [ ] Non-Git Project
- [ ] Deleted File
- [ ] Unsupported Binary
- [ ] Large File
- [ ] Large Diff
- [ ] Invalid Encoding 不 Crash
- [ ] Missing VS Code 有提示
- [ ] External Process Launch Failure 有反馈

## Performance

- [ ] Full Process Tree RAM
- [ ] Phase 1 Baseline
- [ ] Idle CPU 接近零
- [ ] 启动不全项目扫描
- [ ] V1 无常驻全文 File Index
- [ ] 无高频 Git Poll
- [ ] Watcher Debounce
- [ ] Git Debounce
- [ ] Inactive Viewer Unmount
- [ ] Inactive PDF Release
- [ ] Large Diff Backend 截断
- [ ] RAM 明显低于同场景 VS Code

---

# 189. Scope Guard

以下提议默认拒绝 V1：

```text
“加 Terminal”
```

拒绝。

```text
“Code Viewer 顺便编辑”
```

拒绝。

```text
“加 Git Commit”
```

拒绝。

```text
“加 Push / Pull”
```

拒绝。

```text
“加 Debugger”
```

拒绝。

```text
“加 Extension”
```

拒绝。

```text
“做内置 Browser”
```

拒绝。

```text
“自动识别并运行所有 Python/Node 项目”
```

拒绝。

```text
“整个 File Tree 支持完整 Manual Sort”
```

拒绝。

---

# 190. V1 产品成功标准

Checklist 全部通过：

> 不等于产品一定成功。

最终还需回答：

### 1. Markdown

是否明显比 VS Code 当前阅读流程方便？

### 2. PDF

是否舒服，同时 Inactive PDF 不长期大量占用 RAM？

### 3. Multi Project

是否可以在一个窗口自然切换多个 AI 项目？

### 4. File Tree

Favorites First 是否真正让人高频关注的文件更容易访问，同时 Agent 新增文件不会制造排序维护负担？

### 5. Git

是否形成清楚的：

```text
Project ●
↓
Git [7]
↓
Changes / Staged Changes
↓
Diff
```

逐层信息结构？

### 6. Git Familiarity

熟悉 VS Code Source Control 的用户是否几乎不需要重新学习？

### 7. Git Scope

Monorepo / Repository Subdirectory 场景下，用户看到的 Git 信息是否仍然符合“当前 Project”的直觉？

### 8. Agent Changes

Agent 修改、删除、Rename 文件后，Viewer 是否稳定跟随？

### 9. RUN / HANDOFF

是否能够自然实现：

```text
小改
→ Notepad

正式编辑
→ VS Code

网页
→ Browser

脚本
→ External Console

程序
→ EXE
```

又没有把应用做成完整 IDE？

### 10. Stability / Resources

大型项目、大文件、大 Diff、扫描 PDF 场景是否稳定，同时 Process Tree 的 RAM、CPU、后台活动明显低于 VS Code？

全部达到：

# AI Project Viewer V1 才算真正完成。

---

# 191. 给 ZCode 的开发纪律

禁止：

> 一次实现整份 V1.5。

必须：

```text
Read full V1.5
↓
Plan current Phase
↓
Identify risks
↓
Implement current Phase only
↓
Compile
↓
Run
↓
Test
↓
Benchmark where required
↓
Fix
↓
Report
↓
STOP
```

只有用户明确要求：

> 才进入下一 Phase。

---

# 192. 给 ZCode 的第一条开发指令

请完整阅读：

> **AI Project Viewer V1.5 FINAL**

本版本是唯一有效的 V1 开发规格。

V1.0–V1.4 全部忽略。

当前只允许：

# Phase 1

开始前：

1. 检查 Windows 开发环境；
2. 确认 Rust / Tauri / Node / Package Manager；
3. 输出整体工程结构；
4. 指出 Phase 1 主要技术风险；
5. 不实现 Phase 2+ 功能。

Phase 1 完成后必须：

1. 成功编译；
2. 实际启动；
3. 验证 Single Instance；
4. 验证 Project Tabs；
5. 验证 Add / Remove / Dedup；
6. 验证 Files / Git / Settings Shell；
7. 验证应用级快捷键基础拦截机制；
8. 执行 Process Tree RAM Benchmark；
9. 执行 Idle CPU Benchmark；
10. 记录 Startup Time；
11. 记录 WebView2 Process Count；
12. 报告问题与技术债；
13. 停止。

不得：

- 自动进入 Phase 2；
- 使用大量 TODO 假装完成；
- 为了 Demo 写不可维护临时代码；
- 未实际运行就宣称完成；
- 自行扩大 Scope。

---

# 193. V1.4 → V1.5 变更审计

本节用于防止需求重写导致 Regression。

V1.5 相对于 V1.4 **只进行了以下明确修改**。

## A. Favorites / Sorting

新增明确规则：

```text
Pinned Area
→ 不受 Folders First 影响
→ 完全按人工 Drag Order

Unpinned Area
→ 受 Folders First 开关控制
→ 自动排序
```

Full Manual Sort：

> 仍保持删除状态，没有重新加入。

---

## B. Git Repository Scope

新增：

- Git Root Detection；
- Project Root 位于父 Repository 中的行为；
- Git Repository / Project Scope UI；
- Badge 只统计 Scope；
- Project Dirty 只统计 Scope；
- Changes / Staged 只显示 Scope；
- File Marks 只显示 Scope；
- Recent Commits Scope-aware；
- Branch / Ahead / Behind 保持 Repository-wide；
- 父目录包含多个 Git Repo 时不递归发现。

原有 VS Code-style Git Review：

> 保持不变。

---

## C. Session Path Persistence

新增明确要求：

- expandedFolders 使用 Project-relative Path；
- Active File 使用 Project-relative identity；
- FileTab persistence 以 relativePath 为主；
- pinnedItems 继续使用 Relative Path。

原有 Atomic State / Debounce：

> 保持不变。

---

## D. AppState

恢复：

```typescript
version: number
```

并加入状态 Migration 基础结构。

---

## E. MSI

左键行为从模糊的：

```text
Unsupported / Info
```

明确为：

```text
Unsupported Viewer
```

其他 MSI 规则不变：

> 不提供普通 Run。

---

## F. PDF Future

恢复 Future：

- PDF TOC；
- PDF Thumbnail Sidebar；

并保留：

- PDF Annotation。

PDF.js V1 主方案：

> 未改变。

---

## G. WebView2 Keyboard Handling

将原“实现提醒”升级为正式规格。

要求：

> 应用快捷键优先于 Browser Accelerator。

新增 Checklist。

---

## H. Release Preparation

Phase 10 新增：

> Release Packaging Decision。

不改变 Phase 1–9 功能范围。

---

## I. 明确未发生变化的核心规格

以下 V1.4 已确认内容在 V1.5 **没有被删除或降级**：

- Single Instance；
- Multi Project Tabs；
- Sidebar Header Files / Git；
- Git Badge；
- Project Clean / Dirty；
- Tree Visibility 与 Watcher Ignore 分离；
- `dist/build/target` Tree 默认显示；
- Favorites First；
- Pin File / Folder；
- Pinned 手动排序；
- No Full Manual Sort；
- Markdown Rendered by Default；
- PDF.js；
- PDF Virtualization；
- PDF Resource Release；
- Fixed File Inspection Pipeline；
- GB18030 Fallback；
- Secure SVG；
- Large File Guard；
- CodeMirror Read-only；
- HTML Browser；
- Modern Web file:// 边界；
- Visible Script Console；
- EXE Run；
- MSI No Run；
- Project Trust；
- Notepad Quick Edit；
- VS Code Full Edit；
- ExternalEditor Abstraction；
- Frontend No Arbitrary Execute；
- VS Code-style Read-only Git Panel；
- Changes / Staged Changes；
- Same File May Exist in Both；
- Git Safe Review；
- Diff Size Guard；
- Active Project Watch；
- Delete / Rename Handling；
- Updated Toast；
- Non-Git Graceful Degradation；
- Git Missing Graceful Degradation；
- Core Keyboard Shortcuts；
- Complete Engineering Checklist；
- Process-tree RAM Benchmark；
- Phase-by-phase Development Discipline；
- Scope Guard。

---

# 194. 最终产品闭环

```text
┌───────────────────────────────┐
│ Codex / ZCode / Claude Code   │
│                               │
│            DEVELOP            │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       AI Project Viewer       │
│                               │
│ READ                          │
│ Files / Markdown / PDF / Code │
│                               │
│ REVIEW                        │
│ Git / Changes / Diff          │
│                               │
│ RUN                           │
│ Browser / Script / EXE        │
│                               │
│ HANDOFF                       │
│ Notepad / VS Code / Explorer  │
└───────────────────────────────┘
```

AI Agent：

> 负责主要开发。

AI Project Viewer：

> 负责人的项目观察、阅读、Review 和轻量控制。

Notepad：

> 负责快速小修改。

VS Code：

> 负责真正需要人工介入的完整编辑和调试。

---

# 195. 最终原则

本项目最重要的不是：

> 实现尽可能多的 IDE 功能。

而是：

> **在 Agent 承担主要编码工作的时代，让用户以更低资源消耗、更适合阅读和 Review 的方式，高效掌握多个项目正在发生什么。**

任何新增需求都必须首先判断：

```text
属于 READ？

属于 REVIEW？

属于 RUN？

属于 HANDOFF？
```

如果全部不是：

> 默认拒绝。

即使属于其中之一，也必须继续判断：

> 价值是否足以抵消 RAM、复杂度、后台活动和维护成本？

始终坚持：

# Small, Fast, Focused.

---

# 196. 定稿评审附注（ZCode）

> 本节为 V1.5 定稿评审时 ZCode 提出的附注，**不属于 §1–§195 的正式规格**。
> 附注 A 是对 §65 的事实性修正，建议在 Phase 7 实现前合入正文；
> 附注 B、C 是可选补充，随对应 Phase 顺手落实即可，不阻塞任何开发。

## 附注 A：Git 输出路径基准（修正 §65）——已合入正文（2026-10-10，见 §65 与 §197 审计）

§65 中“Git CLI 通常返回相对于 Git Root 的路径”的表述不完全准确：

```text
git status --porcelain
→ 在子目录运行时，输出相对当前工作目录（cwd）的路径

git diff / git log
→ 输出相对 Git Root 的路径
```

两者基准不一致，按“统一相对 Git Root”的字面理解去解析 status 会出错。

建议规约：

> 所有 Git 命令统一以 `git -C <GitRoot>` 方式执行。

这样全部输出统一相对 Git Root，再统一进行 Scope 过滤与 Project-relative 换算。

实施时机：Phase 7。

## 附注 B：窗口状态持久化（建议）

AppState 目前不包含 Window Bounds（大小、位置、最大化状态）。

重启后窗口回到默认尺寸，体验有损。

建议：

> 持久化 Window Bounds，重启恢复。

实现可用 Tauri window-state 插件，或纳入 AppState。

非必须，可归 Phase 4 或 P1。

## 附注 C：state.json 损坏容错（建议）

§26 的 Atomic Replace 防止了写入过程中的损坏，但无法防御磁盘错误、用户手动编辑出错等场景。

建议启动时：

```text
state.json 解析失败
↓
损坏文件改名备份，例如 state.json.corrupt-<timestamp>
↓
使用默认状态正常启动
↓
不得崩溃退出
```

实施时机：Phase 4。
---

# 197. 增量修订审计(2026-10-01 起,机制沿用 §193)

| 日期 | 节 | 变更 | 出处 |
|---|---|---|---|
| 2026-10-01 | §30 | Files `⋯` 菜单取消;Folders First / Show system folders / Refresh 并入 Settings(⚙ 点进再点回 Files) | owner Phase 2 验收反馈 |
| 2026-10-01 | §33 | 取消 Name / Favorites First 两模式,合并为单一排序制(Pinned 区 + Unpinned 区);Name 模式删除 | owner:"没必要单独保留 name 选项" |
| 2026-10-01 | —(技术性,不改需求) | Windows 下 HTML5 拖拽失效根因 = Tauri 默认 `dragDropEnabled` 拦截;窗口配置改 false(实现细节见 architecture.md §12) | owner:"pin 之间无法拖拽调序" |
| 2026-10-01 | §39(细化) | 拖拽落点语义补全:置顶行上/下半=插前/插后;置顶区上方=插到最顶(原"甩到顶"落死区) | owner:"移动不到最顶部,别的位置可以" |
| 2026-10-01 | §86/§108(细化) | Rendered\|Source、Formatted\|Source 切换入口由查看器内浮动按钮改为**文件页签右键菜单** | owner:"右边又开一个窗口多难看" |
| 2026-10-01 | §186(提前) | "Pin File Tab" 由 P1 提前入 V1:页签默认正常累积;任一页签被"固定"后,新文件顶替未固定页签(顶当前未固定者,其次最后一个未固定者),防堆积(同日二次澄清:首版误做成 VS Code 全预览模型,已改口) | owner 第 8 条+当日澄清 |
| 2026-10-01 | §111(泛化,提前) | 新增右键 "Open with Default App"(opener 直达系统关联程序,不经资源管理器),承接应用内不可看格式(视频等) | owner 第 10 条:"常见类型不要跳出去" |
| 2026-10-01 | —(技术性) | 图片路由修正:JPEG/PNG/GIF 字节天然含 NULL 被文本二进制判定拦截,改为扩展名优先走媒体通道;视觉打磨:浅色阅读面纯白/字体栈 Segoe UI Variable+Cascadia/查看器字号设置(§155 范围) | owner 第 3/6/7/10 条 |
| 2026-10-01 | §22(增量) | AppSettings 新增 `viewer.fontSize`(默认 13),字号设置归位应用级设置并随 Phase 4 持久化;同批 §17 落地时 sortMode 字段随 §33 修订自然消失 | Phase 4(spec-004 D8) |
| 2026-10-09 | §16(修正) | 关闭行为从"最小化到任务栏主区"改为"隐藏到系统托盘":托盘单击恢复、右键菜单 Show/Exit(Exit=唯一退出,落盘后退出) | owner 澄清:"想让这个图标到我画框的那个里面"(系统托盘) |
| 2026-10-02 | §16(增量) | 窗口关闭行为:点关闭=最小化到任务栏不退出;任务栏图标右键"关闭窗口"=真退出(按"是否已最小化"区分两种关闭请求) | owner 指令:"关闭这个软件的时候,它是最小化到任务栏……右键才能选择退出" |
| 2026-10-02 | §6(增量) | "低资源占用"升格为全程第一实现原则(内存最小化):每个开发决策过内存秤,能不驻留不驻留/延迟加载/关闭即释放;"先做完再优化"不被接受 | owner 立规:"要始终秉承一个原则:让内存最小化" |
| 2026-10-01 | §17(增量) | sidebarWidth 交互澄清:侧栏可拖拽调宽(200–600)+键盘步进,按项目持久化;原文档仅有字段无交互明文,Phase 4 首交未做,owner 验收后拍板补上 | owner:"要拖拽" |
| 2026-10-10 | §86(增量,翻案) | MD 阅读列宽度上限(860px)删除,渲染态文本铺满文本区——居中后两侧空带在宽窗口仍"很明显",上限本身才是空白之源;字号可读性由工具栏全局字号调节承担 | owner 二轮反馈:"MD 右侧的空白还是很明显";同轮立规:版本固定 0.6.x 递增不跳段 |
| 2026-10-10 | §86/§100/§107/§108(增量) | 文本类查看器(MD/代码/JSON)顶部增统一操作栏:字号调节(操作全局 §22 viewer.fontSize,与 Settings 同旋钮)+ Find in Document(命中计数+上下条跳转,页导航级,同 §92 PDF 搜索先例);Ctrl+F 统一聚焦当前查看器 Find 框(PDF 含);MD 渲染态阅读列 860px 上限保留但居中(原左贴边在宽窗口呈"右侧空白"误判;**0.6.1 改口:上限删除、文本铺满,居中不足以消空白——见下行**) | owner 指令:"都应该模仿 PDF,设置一个对文本区进行操作的'操作栏'…还有一个 Find in Document"+"MD 最大化后右边冒出空白区域" |
| 2026-10-10 | §30(增量) | Refresh 入口由 Settings 迁至侧栏头部 ⚙ 左侧 ↻ 图标(无文字,点击有旋转反馈,忙碌防连点);同批树行为细化(§27):展开/重展开与项目切换一律重新读盘,不再整会话吃旧缓存(空文件夹可自救),新建顶层目录仍需 Refresh | owner 指令:"把这个 Refresh 放到 Settings 的左侧,但不用显示这个单词"+"点击的时候应该有一个明显的效果";"文件夹里增加了文件,仍然是空的"报障 |
| 2026-10-10 | §27(增量) | 树高亮唯一真源=当前激活页签(旧 selectedRelPath 点击态与页签走岔已删);激活文件时树自动展开祖先链并滚动定位(VS Code reveal);三右键菜单视口钳制 | owner:"左侧文件树高亮显示的文件和文件区高亮显示的文件不一致";"模仿 VSCode…自动展开并高亮";"左下角文件右键菜单显示不完整" |
| 2026-10-10 | §65(修正合入) | 定稿附注 A 合入正文:所有 Git 命令统一 `git -C <GitRoot>` 执行,输出基准统一相对 Git Root(status 在子目录 cwd 与 diff/log 的 Git Root 基准不一致) | §196 附注 A(Phase 7 前合入的既定安排) |
| 2026-10-10 | §54(增量) | Recent Commits 由纯展示改为可点击:点击提交 → 查看区打开提交详情(Message/作者/日期/Hash/涉及文件),文件可再点入该提交视角 diff;Git 查看区接管主区时隐藏普通文件页签行 | owner 0.6.7 验收:"点击以后没有任何反应……可以出一个弹窗,也可以在右侧展开" |
| 2026-10-10 | §71(提前) | Side-by-side 并排 diff 由 P1 提前入 Phase 7:owner 0.6.7 验收对照 VS Code 指出单栏不满足;连带定稿 Git 面板视觉基调=对齐 VS Code Source Control(分段文件名/目录、字母右置、计数徽章、提交图形列) | owner 0.6.7 验收:"你先模仿 VSCode"+"VSCode 那个是并排窗口对比展示" |
| 2026-10-10 | —(技术性) | 提交相对时间单位修正:git %ct 为秒,前端需毫秒,曾显示 "56y ago";已在 Rust 层 ×1000 并加测试 | owner 截图可见 "56y ago" |
| 2026-10-11 | §119(修订) | Run 成功反馈由 "✓ x launched" Toast 改为**无提示**(可见控制台即反馈);失败由角落 Toast 改为**窗口正中的错误弹窗**(标题+具体原因,OK/Esc 关闭) | owner:"成功的话直接弹出来就行…不要再显示那个横幅。如果不成功,应该在窗口正中间弹出一个错误信息窗口,并且说清楚错误原因" |
| 2026-10-11 | §164(增量) | Settings 诊断区撤下 Channel/Build/Startup/Shortcut 读数,**只留 Export Diagnostics 按钮**(读数仍进导出报告;测量本身不变) | owner:"这都是什么乱七八糟的信息啊…你不就留一个这个 Export 的按钮不就完了吗" |
| 2026-10-10 | §27(增量) | 树高亮补充右键语义:某行的右键菜单打开期间,该行**独占**高亮(恰好一行常亮);菜单关闭即还原"唯一真源=激活页签"——不做粘滞右键选中,避免重造两套真值 | owner 0.6.11 复验:"右键 Example.url,Example 并没有高显,之前的 styles.css 反而高显" |
