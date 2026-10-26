/**
 * UI string dictionary (owner 2026-10-26 requirement: in-app language
 * switch English/简体中文, default English).
 *
 * PURE module — no store imports, no Svelte — so the dictionary and the
 * en/zh key parity are unit-testable under plain vitest. The reactive
 * accessor lives in t.svelte.ts.
 *
 * Conventions:
 * - Keys are flat "area.name" ids; both locales carry the exact same key
 *   set (enforced by the Record<I18nKey, string> type on `zh` and by a
 *   vitest parity guard).
 * - Strings with variables use {name} placeholders; format via tf().
 * - File CONTENT is never translated (it is the user's data); the app
 *   name "AI Project Viewer" and product names (Git, VS Code) stay as-is.
 * - zh wording follows VS Code / Windows 简体中文 conventions.
 */

export type Locale = "en" | "zh";

export const en = {
  // --- common ---
  "common.loading": "Loading…",
  "common.close": "Close",
  "common.ok": "OK",
  "common.copy": "Copy",
  "common.emptyFolder": "Empty folder",
  "common.cancel": "Cancel",
  "common.dismiss": "Dismiss",
  "common.noProject": "No project open.",
  "common.sidebarWidth": "Sidebar width",

  // --- sidebar header ---
  "header.files": "Files",
  "header.git": "Git",
  "header.refresh": "Refresh",
  "header.settings": "Settings",

  // --- handoff / context menus (handoffMenu.ts + menu components) ---
  "menu.open": "Open",
  "menu.editNotepad": "Edit in Notepad",
  "menu.openVscode": "Open in VS Code",
  "menu.openFolderVscode": "Open Folder in VS Code",
  "menu.openBrowser": "Open in Browser",
  "menu.openDefaultApp": "Open with Default App",
  "menu.openDefaultPdfApp": "Open with Default PDF App",
  "menu.runScript": "Run Script",
  "menu.run": "Run",
  "menu.showExplorer": "Show in File Explorer",
  "menu.openExplorer": "Open in File Explorer",
  "menu.openProjectVscode": "Open Project in VS Code",
  "menu.copyAbs": "Copy Absolute Path",
  "menu.copyRel": "Copy Relative Path",
  "menu.copyProject": "Copy Project Path",
  "menu.properties": "Properties",
  "menu.pinTop": "Pin to Top",
  "menu.unpin": "Unpin",
  "menu.pinTab": "Pin Tab",
  "menu.unpinTab": "Unpin Tab",
  "menu.viewRendered": "View Rendered",
  "menu.viewSource": "View Source",
  "menu.viewFormatted": "View Formatted",
  "menu.closeTab": "Close Tab",
  "menu.closeOthers": "Close Others",
  "menu.closeLeft": "Close to the Left",
  "menu.closeRight": "Close to the Right",
  "menu.refreshProject": "Refresh Project",
  "menu.removeProject": "Remove Project",
  "menu.untrustProject": "Untrust Project",
  "menu.trustProject": "Trust Project for Execution",
  "menu.kindFolder": "folder",
  "menu.kindFile": "file",
  // noun phrases for the copy toast ("Copied absolute path: …")
  "what.absolutePath": "absolute path",
  "what.relativePath": "relative path",
  "what.projectPath": "project path",

  // --- trust gate dialog (run with trust) ---
  "trust.title": "Trust Project",
  "trust.body":
    "This project contains executable files.\n\nRunning scripts or programs can modify files or your system.",
  "trust.ok": "Trust and Run",
  "trust.nowToast": "\u201c{name}\u201d is now trusted for execution.",
  "trust.noLongerToast": "\u201c{name}\u201d is no longer trusted for execution.",

  // --- dialogs ---
  "props.size": "Size",
  "props.modified": "Modified",
  "props.created": "Created",
  "props.accessed": "Accessed",
  "props.history": "History",
  "props.historyGit": "(git)",
  "props.noHistory": "No recorded changes.",
  "props.loadingHistory": "Loading history…",
  "props.aria": "Properties: {name}",
  "props.removeTitle": "Remove Project",
  "props.removeBody":
    'Remove "{name}" from AI Project Viewer?\n\nThe folder on disk is not modified or deleted.',
  "props.removedToast": 'Removed "{name}" (folder untouched on disk).',

  // --- update button (experience channel) ---
  "update.label": "Update",
  "update.updating": "Updating…",
  "update.titleAvail": "Version {v} — update available: {note}",
  "update.titleCurrent": "Version {v} — you are on the latest build",
  "update.upToDate": "Up to date",
  "update.checking": "Checking…",
  "update.readyTitle": "Update Ready",
  "update.readyAsk": "Update installed. Restart AI Project Viewer now?",
  "update.restartNow": "Restart Now",
  "update.later": "Later",
  "update.installedToast": "✓ Update installed — it takes effect on next launch",
  "update.failedToast": "Update failed: {err}",
  "update.latestToast": "You are on the latest version",

  // --- settings panel ---
  "settings.fileTree": "File Tree",
  "settings.foldersFirst": "Folders First",
  "settings.refreshHint": "Refresh lives in the sidebar header (circular-arrow icon, left of the gear).",
  "settings.visibility": "Visibility",
  "settings.showSystemFolders": "Show system/generated folders",
  "settings.appliesHint": "Applies to every project (V1.5 §22 AppSettings).",
  "settings.viewer": "Viewer",
  "settings.fontSize": "Font size",
  "settings.smallerFont": "Smaller font",
  "settings.largerFont": "Larger font",
  "settings.externalEditors": "External Editors",
  "settings.openInVscode": "Open in VS Code",
  "settings.newWindow": "New Window",
  "settings.reuseWindow": "Reuse Existing Window",
  "settings.theme": "Theme",
  "settings.themePaper": "Warm Paper",
  "settings.themeGlacier": "Glacier Blue",
  // Language names render in their OWN language (standard practice).
  "settings.language": "Language",
  "settings.langEn": "English",
  "settings.langZh": "简体中文",
  "settings.diagnostics": "Diagnostics",
  "settings.exportDiag": "Export Diagnostics",
  "settings.exporting": "Exporting…",

  // --- welcome / empty state + add-project menu ---
  "empty.openFirst": "Open your first project",
  "empty.openFolder": "Open Folder",
  "empty.recent": "Recent",
  "empty.tagline": "Read. Review. Run. Hand off.",
  "addMenu.browse": "Browse for Folder…",
  "addMenu.openRecent": "Open Recent",
  "addMenu.clearRecent": "Clear Recent",
  "addMenu.removeFromRecent": "Remove from recent",
  "addMenu.addProject": "Add project",

  // --- git panel ---
  "git.noProject": "No project open.",
  "git.missing1": "Git is not installed or cannot be found.",
  "git.missing2": "Git review is unavailable.",
  "git.missing3": "File browsing remains available.",
  "git.notRepo": "This folder is not a Git repository.",
  "git.unreadable": "Git state could not be read.",
  "git.repository": "Repository:",
  "git.scope": "Scope:",
  "git.changes": "Changes",
  "git.staged": "Staged Changes",
  "git.commits": "Recent Commits",
  "git.noChanges": "No changes.",
  "git.noCommits": "No commits yet.",
  "git.retry": "Retry",
  "git.upstream": "Upstream: {name}",
  "git.kindStaged": "(Staged)",
  "git.kindWorktree": "(Working Tree)",

  // --- viewers ---
  "viewer.findPlaceholder": "Find in document…",
  "viewer.searchDoc": "Search document",
  "viewer.rendered": "Rendered",
  "viewer.source": "Source",
  "viewer.formatted": "Formatted",
  "viewer.invalidJson": "Invalid JSON — showing source.",
  "viewer.fit": "Fit",
  "viewer.actual100": "100%",
  "viewer.fitWidth": "Fit Width",
  "viewer.fitPage": "Fit Page",
  "viewer.prevPage": "Previous page",
  "viewer.nextPage": "Next page",
  "viewer.zoomIn": "Zoom in",
  "viewer.zoomOut": "Zoom out",
  "viewer.prevMatch": "Previous match",
  "viewer.nextMatch": "Next match",
  "viewer.pageAria": "Page number",
  "viewer.smallerText": "Smaller text",
  "viewer.largerText": "Larger text",
  "viewer.imageControls": "Image controls",
  "viewer.author": "Author",
  "viewer.date": "Date",
  "viewer.hash": "Hash",
  "viewer.filesChanged": "FILES CHANGED",
  "viewer.noScopedFiles": "No files in this project's scope.",
  "viewer.deleted": "This file has been deleted.",
  "viewer.binaryNote": "Binary file — not shown as text.",
  "viewer.tooLarge": "File is larger than 20 MB and will not be opened in the viewer.",
  "viewer.cannotDisplay": "Cannot display this file.",
  "viewer.mediaKind": "Media file (video/audio)",
  "viewer.sizeLabel": "Size:",
  "viewer.modifiedLabel": "Modified:",
  "viewer.pathLabel": "Path:",
  "viewer.cannotPreview": "This file cannot be previewed in the app.",
  "viewer.cannotPreviewPlain": "This file cannot be previewed.",
  "viewer.openDefaultAppBtn": "Open with Default App",
  "viewer.openInPlayer": "Open in Default Player",
  "viewer.openingBtn": "Opening…",
  "viewer.runningBtn": "Running…",
  "viewer.showExplorerBtn": "Show in File Explorer",
  "viewer.execKind": "Windows Executable",
  "viewer.diffTooLarge": "Diff is too large to display.",
  "viewer.openInVscodeBtn": "Open in VS Code",
  "viewer.openAFileHint": "Open a file from the tree to view it.",
  "viewer.projectFiles": "Project files",
  "viewer.openFiles": "Open files",
  "viewer.findNoResults": "0 results",
  "viewer.closeDiff": "Close diff",
  "viewer.noTextChanges": "No textual changes.",
  "viewer.noTextChangesBinary": "No textual changes (binary file).",
  "viewer.noMessage": "(no message)",
  "viewer.hugeTitle": "Large File",
  "viewer.hugeBody": "{name} is {size} MB.\n\nOpening this file may affect performance.",
  "viewer.openAnyway": "Open Anyway",
  "viewer.cannotRender": "Cannot render PDF: {err}",
  "viewer.fileContent": "File content",
  "viewer.loadingPdf": "Loading…",

  // --- toasts / composed messages ---
  "toast.copied": "Copied {what}: {text}",
  "toast.copyFailed": "Copy failed ({what})",
  "toast.actionFailed": "{label} failed: {err}",
  "toast.opening": "Opening {name}…",
  "toast.fileUpdated": "✓ {name} updated",
  "toast.copiedChars": "✓ Copied {n} characters",
  "toast.alreadyOpen": '"{name}" is already open — switched to its tab.',
  "toast.cannotOpenFolder": "Cannot open folder: {err}",
  "toast.cannotOpenPicker": "Cannot open folder picker: {err}",
  "toast.cannotOpenFile": "Cannot open file: {err}",
  "toast.cannotOpenPdf": "Cannot open PDF: {err}",
  "toast.cannotOpenImage": "Cannot open image: {err}",
  "toast.cannotOpenMedia": "Cannot open media: {err}",
  "toast.explorerFailed": "Explorer failed: {err}",
  "toast.diagExported": "Diagnostics exported: {path}",
  "toast.diagExportFailed": "Export failed: {err}",
  "dlg.launchFailedTitle": "Failed to launch {name}",

  // --- relative time (gitFormat) ---
  "time.justNow": "just now",
  "time.mAgo": "{n}m ago",
  "time.hAgo": "{n}h ago",
  "time.yesterday": "yesterday",
  "time.dAgo": "{n}d ago",
  "time.wAgo": "{n}w ago",
  "time.moAgo": "{n}mo ago",
  "time.yAgo": "{n}y ago",
} as const;

export type I18nKey = keyof typeof en;

export const zh: Record<I18nKey, string> = {
  // --- common ---
  "common.loading": "加载中…",
  "common.close": "关闭",
  "common.ok": "确定",
  "common.copy": "复制",
  "common.emptyFolder": "空文件夹",
  "common.cancel": "取消",
  "common.dismiss": "关闭提示",
  "common.noProject": "未打开项目。",
  "common.sidebarWidth": "侧栏宽度",

  // --- sidebar header ---
  "header.files": "文件",
  "header.git": "Git",
  "header.refresh": "刷新",
  "header.settings": "设置",

  // --- handoff / context menus ---
  "menu.open": "打开",
  "menu.editNotepad": "在记事本中编辑",
  "menu.openVscode": "在 VS Code 中打开",
  "menu.openFolderVscode": "在 VS Code 中打开文件夹",
  "menu.openBrowser": "在浏览器中打开",
  "menu.openDefaultApp": "用默认应用打开",
  "menu.openDefaultPdfApp": "用默认 PDF 应用打开",
  "menu.runScript": "运行脚本",
  "menu.run": "运行",
  "menu.showExplorer": "在资源管理器中显示",
  "menu.openExplorer": "在资源管理器中打开",
  "menu.openProjectVscode": "在 VS Code 中打开项目",
  "menu.copyAbs": "复制绝对路径",
  "menu.copyRel": "复制相对路径",
  "menu.copyProject": "复制项目路径",
  "menu.properties": "属性",
  "menu.pinTop": "置顶",
  "menu.unpin": "取消置顶",
  "menu.pinTab": "置顶页签",
  "menu.unpinTab": "取消页签置顶",
  "menu.viewRendered": "查看渲染",
  "menu.viewSource": "查看源码",
  "menu.viewFormatted": "查看格式化",
  "menu.closeTab": "关闭页签",
  "menu.closeOthers": "关闭其他页签",
  "menu.closeLeft": "关闭左侧页签",
  "menu.closeRight": "关闭右侧页签",
  "menu.refreshProject": "刷新项目",
  "menu.removeProject": "移除项目",
  "menu.untrustProject": "取消信任项目",
  "menu.trustProject": "信任项目以运行",
  "menu.kindFolder": "文件夹",
  "menu.kindFile": "文件",
  "what.absolutePath": "绝对路径",
  "what.relativePath": "相对路径",
  "what.projectPath": "项目路径",

  // --- trust gate dialog ---
  "trust.title": "信任项目",
  "trust.body": "此项目包含可执行文件。\n\n运行脚本或程序可能修改文件或你的系统。",
  "trust.ok": "信任并运行",
  "trust.nowToast": "“{name}”现已信任执行。",
  "trust.noLongerToast": "“{name}”已不再信任执行。",

  // --- dialogs ---
  "props.size": "大小",
  "props.modified": "修改时间",
  "props.created": "创建时间",
  "props.accessed": "访问时间",
  "props.history": "历史记录",
  "props.historyGit": "(git)",
  "props.noHistory": "暂无修改记录。",
  "props.loadingHistory": "正在加载历史…",
  "props.aria": "属性:{name}",
  "props.removeTitle": "移除项目",
  "props.removeBody": "从 AI Project Viewer 移除“{name}”?\n\n磁盘上的文件夹不会被修改或删除。",
  "props.removedToast": "已移除“{name}”(磁盘上的文件夹未动)。",

  // --- update button ---
  "update.label": "更新",
  "update.updating": "更新中…",
  "update.titleAvail": "版本 {v} —— 有可用更新:{note}",
  "update.titleCurrent": "版本 {v} —— 已是最新构建",
  "update.upToDate": "已是最新",
  "update.checking": "检查中…",
  "update.readyTitle": "更新就绪",
  "update.readyAsk": "更新已安装。现在重启 AI Project Viewer 吗?",
  "update.restartNow": "立即重启",
  "update.later": "稍后",
  "update.installedToast": "✓ 更新已安装——下次启动生效",
  "update.failedToast": "更新失败:{err}",
  "update.latestToast": "已是最新版本",

  // --- settings panel ---
  "settings.fileTree": "文件树",
  "settings.foldersFirst": "文件夹优先",
  "settings.refreshHint": "刷新在侧栏顶部(齿轮左边的循环箭头)。",
  "settings.visibility": "显示",
  "settings.showSystemFolders": "显示系统/生成文件夹",
  "settings.appliesHint": "对所有项目生效。",
  "settings.viewer": "查看器",
  "settings.fontSize": "字号",
  "settings.smallerFont": "减小字号",
  "settings.largerFont": "增大字号",
  "settings.externalEditors": "外部编辑器",
  "settings.openInVscode": "在 VS Code 中打开",
  "settings.newWindow": "新窗口",
  "settings.reuseWindow": "复用已有窗口",
  "settings.theme": "主题",
  "settings.themePaper": "暖纸书卷",
  "settings.themeGlacier": "冰川蓝",
  "settings.language": "语言",
  "settings.langEn": "English",
  "settings.langZh": "简体中文",
  "settings.diagnostics": "诊断",
  "settings.exportDiag": "导出诊断信息",
  "settings.exporting": "导出中…",

  // --- welcome / empty state + add-project menu ---
  "empty.openFirst": "打开你的第一个项目",
  "empty.openFolder": "打开文件夹",
  "empty.recent": "最近打开",
  "empty.tagline": "阅读 · 检视 · 运行 · 移交",
  "addMenu.browse": "浏览文件夹…",
  "addMenu.openRecent": "最近打开",
  "addMenu.clearRecent": "清空最近记录",
  "addMenu.removeFromRecent": "从最近记录移除",
  "addMenu.addProject": "添加项目",

  // --- git panel ---
  "git.noProject": "未打开项目。",
  "git.missing1": "未安装 Git 或无法找到。",
  "git.missing2": "Git 检视不可用。",
  "git.missing3": "文件浏览不受影响。",
  "git.notRepo": "此文件夹不是 Git 仓库。",
  "git.unreadable": "无法读取 Git 状态。",
  "git.repository": "仓库:",
  "git.scope": "范围:",
  "git.changes": "更改",
  "git.staged": "已暂存的更改",
  "git.commits": "最近提交",
  "git.noChanges": "无更改。",
  "git.noCommits": "暂无提交。",
  "git.retry": "重试",
  "git.upstream": "上游:{name}",
  "git.kindStaged": "(已暂存)",
  "git.kindWorktree": "(工作区)",

  // --- viewers ---
  "viewer.findPlaceholder": "在文档中查找…",
  "viewer.searchDoc": "搜索文档",
  "viewer.rendered": "渲染",
  "viewer.source": "源码",
  "viewer.formatted": "格式化",
  "viewer.invalidJson": "JSON 无效——显示源码。",
  "viewer.fit": "适应",
  "viewer.actual100": "100%",
  "viewer.fitWidth": "适应宽度",
  "viewer.fitPage": "适应页面",
  "viewer.prevPage": "上一页",
  "viewer.nextPage": "下一页",
  "viewer.zoomIn": "放大",
  "viewer.zoomOut": "缩小",
  "viewer.prevMatch": "上一个匹配",
  "viewer.nextMatch": "下一个匹配",
  "viewer.pageAria": "页码",
  "viewer.smallerText": "减小字号",
  "viewer.largerText": "增大字号",
  "viewer.imageControls": "图片控制",
  "viewer.author": "作者",
  "viewer.date": "日期",
  "viewer.hash": "哈希",
  "viewer.filesChanged": "改动的文件",
  "viewer.noScopedFiles": "此项目范围内没有文件。",
  "viewer.deleted": "此文件已被删除。",
  "viewer.binaryNote": "二进制文件——不以文本显示。",
  "viewer.tooLarge": "文件超过 20 MB,不在查看器中打开。",
  "viewer.cannotDisplay": "无法显示此文件。",
  "viewer.mediaKind": "媒体文件(视频/音频)",
  "viewer.sizeLabel": "大小:",
  "viewer.modifiedLabel": "修改时间:",
  "viewer.pathLabel": "路径:",
  "viewer.cannotPreview": "此文件无法在应用内预览。",
  "viewer.cannotPreviewPlain": "此文件无法预览。",
  "viewer.openDefaultAppBtn": "用默认应用打开",
  "viewer.openInPlayer": "用默认播放器打开",
  "viewer.openingBtn": "正在打开…",
  "viewer.runningBtn": "运行中…",
  "viewer.showExplorerBtn": "在资源管理器中显示",
  "viewer.execKind": "Windows 可执行文件",
  "viewer.diffTooLarge": "差异过大,无法显示。",
  "viewer.openInVscodeBtn": "在 VS Code 中打开",
  "viewer.openAFileHint": "从左侧文件树打开一个文件开始查看。",
  "viewer.projectFiles": "项目文件",
  "viewer.openFiles": "打开的文件",
  "viewer.findNoResults": "无结果",
  "viewer.closeDiff": "关闭差异",
  "viewer.noTextChanges": "无文本改动。",
  "viewer.noTextChangesBinary": "无文本改动(二进制文件)。",
  "viewer.noMessage": "(无提交说明)",
  "viewer.hugeTitle": "大文件",
  "viewer.hugeBody": "{name} 大小为 {size} MB。\n\n打开此文件可能影响性能。",
  "viewer.openAnyway": "仍要打开",
  "viewer.cannotRender": "无法渲染 PDF:{err}",
  "viewer.fileContent": "文件内容",
  "viewer.loadingPdf": "加载中…",

  // --- toasts / composed messages ---
  "toast.copied": "已复制{what}:{text}",
  "toast.copyFailed": "复制失败({what})",
  "toast.actionFailed": "{label}失败:{err}",
  "toast.opening": "正在打开 {name}…",
  "toast.fileUpdated": "✓ {name} 已更新",
  "toast.copiedChars": "✓ 已复制 {n} 个字符",
  "toast.alreadyOpen": "“{name}”已打开——已切换到它的页签。",
  "toast.cannotOpenFolder": "无法打开文件夹:{err}",
  "toast.cannotOpenPicker": "无法打开文件夹选择框:{err}",
  "toast.cannotOpenFile": "无法打开文件:{err}",
  "toast.cannotOpenPdf": "无法打开 PDF:{err}",
  "toast.cannotOpenImage": "无法打开图片:{err}",
  "toast.cannotOpenMedia": "无法打开媒体文件:{err}",
  "toast.explorerFailed": "资源管理器操作失败:{err}",
  "toast.diagExported": "诊断信息已导出:{path}",
  "toast.diagExportFailed": "导出失败:{err}",
  "dlg.launchFailedTitle": "启动 {name} 失败",

  // --- relative time ---
  "time.justNow": "刚刚",
  "time.mAgo": "{n} 分钟前",
  "time.hAgo": "{n} 小时前",
  "time.yesterday": "昨天",
  "time.dAgo": "{n} 天前",
  "time.wAgo": "{n} 周前",
  "time.moAgo": "{n} 个月前",
  "time.yAgo": "{n} 年前",
};

const DICTS: Record<Locale, Record<I18nKey, string>> = { en, zh };

/** Pure lookup with {var} interpolation; unknown vars stay literal. */
export function translate(
  locale: Locale,
  key: I18nKey,
  vars?: Record<string, string | number>,
): string {
  let text: string = DICTS[locale]?.[key] ?? en[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

/** Relative time, locale-aware (gitFormat wording moved here so the
 * Chinese phrasing lives with the rest of the dictionary). */
export function relativeTimeDict(
  locale: Locale,
  now: number,
  ts: number,
): string {
  const s = Math.max(0, Math.floor((now - ts) / 1000));
  const t = (key: I18nKey, vars?: Record<string, string | number>) =>
    translate(locale, key, vars);
  if (s < 60) return t("time.justNow");
  const m = Math.floor(s / 60);
  if (m < 60) return t("time.mAgo", { n: m });
  const h = Math.floor(m / 60);
  if (h < 24) return t("time.hAgo", { n: h });
  const d = Math.floor(h / 24);
  if (d === 1) return t("time.yesterday");
  if (d < 7) return t("time.dAgo", { n: d });
  const w = Math.floor(d / 7);
  if (w < 5) return t("time.wAgo", { n: w });
  const mo = Math.floor(d / 30);
  if (mo < 12) return t("time.moAgo", { n: mo });
  return t("time.yAgo", { n: Math.floor(d / 365) });
}
