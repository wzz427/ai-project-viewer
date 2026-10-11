//! Git review (V1.5 §43–§78, spec-007) — a READ-ONLY Source Control view.
//!
//! Every git call goes through [`run_git`]/[`run_git_capped`]: fixed argv
//! (never a shell), the §70 safe-review flags (`--no-pager`,
//! `-c core.quotepath=false`, diff-only `--no-ext-diff --no-textconv`),
//! the §65 unified basis `git -C <GitRoot>` (all output relative to the
//! git root, then scope-filtered and converted to PROJECT-relative paths
//! before crossing the bridge), and a hard timeout so a hung repo can
//! never wedge the UI. `git_diff`'s incoming rel is validated component-
//! wise against `..` escapes (§144 spirit): staged deletions have no file
//! on disk to canonicalize, so the check happens on the path itself.

use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

use serde::Serialize;

const GIT_TIMEOUT: Duration = Duration::from_secs(10);

/// §72 Diff Size Guard: backend stops sending at whichever cap hits first.
const DIFF_MAX_BYTES: usize = 2 * 1024 * 1024;
const DIFF_MAX_LINES: usize = 20_000;

// ---------------------------------------------------------------------------
// Process layer (spec-007: one spawn path, timeout + caps, no console flash).

#[derive(Debug)]
struct RunError {
    missing: bool,
    #[allow(dead_code)]
    timeout: bool,
    message: String,
}

impl RunError {
    fn msg(m: impl Into<String>) -> Self {
        RunError { missing: false, timeout: false, message: m.into() }
    }
}

/// CREATE_NO_WINDOW: git.exe is a console app — without this every refresh
/// flashes a cmd window on the owner's desktop.
#[cfg(target_os = "windows")]
fn no_console_flash(cmd: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(target_os = "windows"))]
fn no_console_flash(_cmd: &mut Command) {}

struct CappedOutput {
    text: String,
    truncated: bool,
    /// Number of '\n' in `text` (the guard's own counter, not a re-count).
    lines: usize,
}

fn spawn(args: &[String]) -> std::io::Result<Child> {
    let mut cmd = Command::new("git");
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    no_console_flash(&mut cmd);
    cmd.spawn()
}

fn io_kind_missing(e: &std::io::Error) -> bool {
    matches!(e.kind(), std::io::ErrorKind::NotFound)
}

/// Run git to completion, bounded by `max_bytes`/`max_lines` and the global
/// timeout. Reading happens on a worker thread with the caps applied
/// incrementally, so a runaway `git diff` never buffers whole in memory —
/// the child is killed the moment either cap trips (§72 "stop sending").
fn run_git_capped(
    args: &[String],
    max_bytes: usize,
    max_lines: usize,
) -> Result<CappedOutput, RunError> {
    let mut child = spawn(args).map_err(|e| {
        if io_kind_missing(&e) {
            RunError { missing: true, timeout: false, message: String::new() }
        } else {
            RunError::msg(format!("cannot start git: {e}"))
        }
    })?;

    let out_pipe = child.stdout.take();
    let truncated = Arc::new(AtomicBool::new(false));
    let trunc_flag = Arc::clone(&truncated);
    let reader = std::thread::spawn(move || {
        let mut bytes: Vec<u8> = Vec::new();
        let mut lines = 0usize;
        let mut buf = [0u8; 64 * 1024];
        if let Some(mut pipe) = out_pipe {
            loop {
                match pipe.read(&mut buf) {
                    Ok(0) => break,
                    Ok(n) => {
                        lines += buf[..n].iter().filter(|&&b| b == b'\n').count();
                        let room = max_bytes.saturating_sub(bytes.len());
                        bytes.extend_from_slice(&buf[..n.min(room)]);
                        if n > room || lines > max_lines {
                            trunc_flag.store(true, Ordering::SeqCst);
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
        }
        (bytes, lines)
    });

    // Drain stderr from the START, not after try_wait returns: git can emit
    // megabytes of warnings while still succeeding (broken objects, stale
    // submodules), and an undrained pipe back-pressures the child until our
    // 10 s timeout misreports a call that would have succeeded
    // (spec-012 M6). Spawned here so it runs during the whole wait loop.
    let err_pipe = child.stderr.take();
    let err_reader = std::thread::spawn(move || {
        let mut s = String::new();
        if let Some(mut p) = err_pipe {
            let _ = p.read_to_string(&mut s);
        }
        s
    });

    let deadline = Instant::now() + GIT_TIMEOUT;
    let status = loop {
        if truncated.load(Ordering::SeqCst) {
            let _ = child.kill();
            let _ = child.wait();
            break None;
        }
        match child.try_wait() {
            Ok(Some(status)) => break Some(status),
            Ok(None) if Instant::now() >= deadline => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = reader.join();
                let _ = err_reader.join();
                return Err(RunError {
                    missing: false,
                    timeout: true,
                    message: "git did not finish within 10 s.".into(),
                });
            }
            Ok(None) => std::thread::sleep(Duration::from_millis(20)),
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = reader.join();
                let _ = err_reader.join();
                return Err(RunError::msg(format!("git wait failed: {e}")));
            }
        }
    };

    let (mut bytes, mut lines) = reader.join().unwrap_or_default();
    let stderr = err_reader.join().unwrap_or_default();
    // The reader counts per 64 KB chunk, so a line-cap trip can overshoot
    // by part of a chunk — trim back to the exact cap (§72: stop sending).
    if lines > max_lines {
        let mut seen = 0usize;
        let mut end = bytes.len();
        for (i, &b) in bytes.iter().enumerate() {
            if b == b'\n' {
                seen += 1;
                if seen == max_lines {
                    end = i + 1;
                    break;
                }
            }
        }
        bytes.truncate(end);
        lines = max_lines;
    }
    match status {
        Some(st) if st.success() => Ok(CappedOutput {
            text: String::from_utf8_lossy(&bytes).into_owned(),
            truncated: truncated.load(Ordering::SeqCst),
            lines,
        }),
        Some(st) => Err(RunError::msg(format!(
            "git exited with {}: {}",
            st.code().unwrap_or(-1),
            stderr.trim()
        ))),
        None => {
            // Cap-tripped path: partial output, truncation flag already set.
            Ok(CappedOutput {
                text: String::from_utf8_lossy(&bytes).into_owned(),
                truncated: true,
                lines,
            })
        }
    }
}

/// Small-output convenience (rev-parse / status / log): bounded by generous
/// caps so even a monorepo with thousands of changed files stays safe.
fn run_git(args: &[String]) -> Result<String, RunError> {
    const STATUS_MAX_BYTES: usize = 16 * 1024 * 1024;
    const STATUS_MAX_LINES: usize = 2_000_000;
    run_git_capped(args, STATUS_MAX_BYTES, STATUS_MAX_LINES).map(|o| o.text)
}

/// §65/§70: every invocation starts from this prefix — one working-dir
/// basis (the git root), quotepath off, no opportunistic index lock
/// (agents run git concurrently; we never need to write the index).
fn git_base_args(root: &Path) -> Vec<String> {
    vec![
        "--no-pager".into(),
        "-c".into(),
        "core.quotepath=false".into(),
        "--no-optional-locks".into(),
        "-C".into(),
        root.to_string_lossy().into_owned(),
    ]
}

/// Pure argv builder (unit-asserted for the §70/§72 flags, spec-007 V3).
fn diff_argv(root: &Path, pathspec: &str, staged: bool) -> Vec<String> {
    let mut args = git_base_args(root);
    args.push("diff".into());
    args.push("--no-ext-diff".into());
    args.push("--no-textconv".into());
    if staged {
        args.push("--cached".into());
    }
    args.push("--".into());
    args.push(pathspec.into());
    args
}

// ---------------------------------------------------------------------------
// porcelain=v2 parsing (§69) — pure, fixture-testable.

#[derive(Debug, Default, PartialEq)]
struct ParsedStatus {
    branch: Option<String>,
    upstream: Option<String>,
    ahead: Option<u32>,
    behind: Option<u32>,
    entries: Vec<RawEntry>,
}

#[derive(Debug, Clone, PartialEq)]
struct RawEntry {
    /// git-root-relative, forward slashes.
    path: String,
    /// rename source (git-root-relative), when the entry is a rename.
    orig_path: Option<String>,
    staged_letter: Option<char>,
    worktree_letter: Option<char>,
}

fn parse_status_output(out: &str) -> ParsedStatus {
    let mut p = ParsedStatus::default();
    for line in out.lines() {
        if let Some(rest) = line.strip_prefix("# branch.head ") {
            p.branch = Some(rest.to_string());
        } else if let Some(rest) = line.strip_prefix("# branch.upstream ") {
            p.upstream = Some(rest.to_string());
        } else if let Some(rest) = line.strip_prefix("# branch.ab ") {
            // "+A -B"; either may be missing without an upstream.
            for tok in rest.split_whitespace() {
                if let Some(n) = tok.strip_prefix('+') {
                    p.ahead = n.parse().ok();
                } else if let Some(n) = tok.strip_prefix('-') {
                    p.behind = n.parse().ok();
                }
            }
        } else if line.starts_with('#') || line.starts_with('!') {
            continue; // other headers / ignored entries
        } else if let Some(rest) = line.strip_prefix("? ") {
            p.entries.push(RawEntry {
                path: unquote(rest),
                orig_path: None,
                staged_letter: None,
                worktree_letter: Some('?'),
            });
        } else if let Some(rest) = line.strip_prefix("u ") {
            // u <XY> <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>
            let path = rest.splitn(10, ' ').nth(9).unwrap_or_default();
            p.entries.push(RawEntry {
                path: unquote(path),
                orig_path: None,
                staged_letter: Some('U'),
                worktree_letter: Some('U'),
            });
        } else if let Some(rest) = line.strip_prefix("1 ") {
            // 1 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <path>
            let mut it = rest.splitn(8, ' ');
            let xy = it.next().unwrap_or_default();
            let path = it.nth(6).unwrap_or_default();
            let (x, y) = xy_chars(xy);
            p.entries.push(RawEntry {
                path: unquote(path),
                orig_path: None,
                staged_letter: x,
                worktree_letter: y,
            });
        } else if let Some(rest) = line.strip_prefix("2 ") {
            // 2 <XY> <sub> <mH> <mI> <mW> <hH> <hI> <X><score> <path><TAB><orig>
            // (TAB separator in non-z mode; NUL only with -z, which we
            // never pass — verified against real git 2.52 in the tests.)
            let mut it = rest.splitn(9, ' ');
            let xy = it.next().unwrap_or_default();
            let last = it.nth(7).unwrap_or_default();
            let (path, orig) = match last.split_once('\t') {
                Some((a, b)) => (a, Some(unquote(b))),
                None => (last, None),
            };
            let (x, y) = xy_chars(xy);
            p.entries.push(RawEntry {
                path: unquote(path),
                orig_path: orig,
                staged_letter: x,
                worktree_letter: y,
            });
        }
    }
    p
}

/// X/Y column chars; '.' means "no change on that side" → None.
fn xy_chars(xy: &str) -> (Option<char>, Option<char>) {
    let mut cs = xy.chars();
    let x = cs.next();
    let y = cs.next().or(x);
    (
        x.filter(|&c| c != '.'),
        y.filter(|&c| c != '.'),
    )
}

/// Undo git's C-style path quoting (only triggers for control chars /
/// quotes / TAB — `core.quotepath=false` keeps non-ASCII literal).
/// Full escape set: `\a \b \f \n \r \t \v \" \\` plus up to 3 octal digits
/// (spec-012 L-r2 — the old parser silently mangled `\a`→`a` and passed
/// `\ooo` through as literal text).
fn unquote(s: &str) -> String {
    let Some(inner) = s.strip_prefix('"').and_then(|r| r.strip_suffix('"')) else {
        return s.to_string();
    };
    let chars: Vec<char> = inner.chars().collect();
    let mut out = String::with_capacity(inner.len());
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c != '\\' {
            out.push(c);
            i += 1;
            continue;
        }
        i += 1;
        if i >= chars.len() {
            out.push('\\');
            break;
        }
        let e = chars[i];
        i += 1;
        match e {
            'a' => out.push('\u{07}'),
            'b' => out.push('\u{08}'),
            'f' => out.push('\u{0c}'),
            'n' => out.push('\n'),
            'r' => out.push('\r'),
            't' => out.push('\t'),
            'v' => out.push('\u{0b}'),
            '"' => out.push('"'),
            '\\' => out.push('\\'),
            '0'..='7' => {
                let mut val = e.to_digit(8).unwrap();
                let mut digits = 1;
                while digits < 3 && i < chars.len() && ('0'..='7').contains(&chars[i]) {
                    val = val * 8 + chars[i].to_digit(8).unwrap();
                    i += 1;
                    digits += 1;
                }
                out.push(val as u8 as char);
            }
            other => out.push(other),
        }
    }
    out
}

// ---------------------------------------------------------------------------
// Scope math (§59–§65).

fn in_scope(path: &str, scope: &str) -> bool {
    scope.is_empty() || path == scope || path.starts_with(&format!("{scope}/"))
}

fn to_project_rel(path: &str, scope: &str) -> String {
    if scope.is_empty() {
        path.to_string()
    } else {
        // path == scope (project root itself listed by git) slices past the
        // end and used to panic — release builds abort the whole app
        // (spec-012 L-r1). `get` returns None exactly there → project root.
        path.get(scope.len() + 1..).unwrap_or(".").to_string()
    }
}

/// Project root relative to the git root ("" = normal repo mode). Windows
/// paths compare case-insensitively; git's answer derives from the very
/// string we passed via `-C`, but strip_prefix_ci keeps us safe anyway.
fn scope_of(project: &Path, git_root: &Path) -> Result<String, String> {
    if project == git_root {
        return Ok(String::new());
    }
    strip_prefix_ci(project, git_root)
        .map(|rel| rel.to_string_lossy().replace('\\', "/"))
        .ok_or_else(|| {
            format!(
                "Project folder is not inside the detected git root ({}).",
                git_root.display()
            )
        })
}

fn strip_prefix_ci(path: &Path, base: &Path) -> Option<PathBuf> {
    let p: Vec<_> = path.components().collect();
    let b: Vec<_> = base.components().collect();
    if p.len() < b.len() {
        return None;
    }
    for (pc, bc) in p.iter().zip(b.iter()) {
        let ps = pc.as_os_str().to_string_lossy();
        let bs = bc.as_os_str().to_string_lossy();
        if !ps.eq_ignore_ascii_case(&bs) {
            return None;
        }
    }
    Some(p[b.len()..].iter().collect())
}

// ---------------------------------------------------------------------------
// Snapshot shape (§20 RuntimeGitState basis; camelCase over the bridge).

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct GitChangeEntry {
    pub rel: String,
    pub letter: char,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub orig_rel: Option<String>,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct GitCommit {
    pub hash: String,
    pub author: String,
    pub subject: String,
    /// Committer time in MILLISECONDS (the frontend feeds it straight into
    /// Date.now() deltas; feeding it seconds made every commit read "56y
    /// ago" on the owner's machine, 2026-10-10).
    pub ts: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GitSnapshot {
    /// "ok" | "nonGit" | "gitMissing" | "error" (§152/§153 states folded in).
    pub status: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub git_root: Option<String>,
    /// "" = project root IS the git root (§56); else "apps/viewer" (§57).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub scope_rel: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub branch: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub upstream: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ahead: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub behind: Option<u32>,
    pub changes: Vec<GitChangeEntry>,
    pub staged: Vec<GitChangeEntry>,
    pub unique_count: u32,
    pub commits: Vec<GitCommit>,
    pub refreshed_at: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GitDiffResult {
    pub text: String,
    pub truncated: bool,
    pub lines: u32,
}

enum SnapErr {
    GitMissing,
    NonGit,
    Error(String),
}

fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

/// Build the two scoped groups + the badge's unique-path count (§53: the
/// same file in both groups still counts once; untracked counts too).
fn scoped_groups(
    entries: &[RawEntry],
    scope: &str,
) -> (Vec<GitChangeEntry>, Vec<GitChangeEntry>, u32) {
    let mut changes = Vec::new();
    let mut staged = Vec::new();
    let mut unique = std::collections::HashSet::new();
    for e in entries {
        if !in_scope(&e.path, scope) {
            continue;
        }
        let rel = to_project_rel(&e.path, scope);
        let orig_rel = e
            .orig_path
            .as_deref()
            .filter(|o| in_scope(o, scope))
            .map(|o| to_project_rel(&o, scope));
        unique.insert(rel.clone());
        if let Some(letter) = e.staged_letter {
            staged.push(GitChangeEntry { rel: rel.clone(), letter, orig_rel: orig_rel.clone() });
        }
        if let Some(letter) = e.worktree_letter {
            changes.push(GitChangeEntry { rel, letter, orig_rel });
        }
    }
    (changes, staged, unique.len() as u32)
}

fn parse_log(out: &str) -> Vec<GitCommit> {
    out.lines()
        .filter(|l| !l.is_empty())
        .filter_map(|l| {
            let mut it = l.splitn(4, '\u{1f}');
            let hash = it.next()?.to_string();
            let author = it.next()?.to_string();
            let ts: u64 = it.next()?.parse().ok()?;
            let subject = it.next()?.to_string();
            Some(GitCommit {
                hash,
                author,
                subject,
                ts: ts.saturating_mul(1000),
            })
        })
        .collect()
}

fn snapshot_inner(project: &Path) -> Result<GitSnapshot, SnapErr> {
    let project = dunce::canonicalize(project)
        .map_err(|e| SnapErr::Error(format!("Project folder is not accessible: {e}")))?;

    // §55 detection: project root → git root.
    let root_out = run_git(
        &with_args(&git_base_args(&project), &["rev-parse", "--show-toplevel"]),
    )
    .map_err(|e| map_run_err(e, "detect git root"))?;
    let git_root = PathBuf::from(root_out.trim());
    let scope = scope_of(&project, &git_root).map_err(SnapErr::Error)?;

    let status_out = run_git(&with_args(
        &git_base_args(&git_root),
        &["status", "--porcelain=v2", "--branch"],
    ))
    .map_err(|e| map_run_err(e, "git status"))?;
    let parsed = parse_status_output(&status_out);
    let (changes, staged, unique_count) = scoped_groups(&parsed.entries, &scope);

    // §54/§64: 20 most recent commits; subdirectory scope limits to commits
    // touching the scope (pathspec is git-root-relative, matching §65).
    let mut log_args = with_args(
        &git_base_args(&git_root),
        &["log", "-n", "20", "--pretty=format:%h%x1f%an%x1f%ct%x1f%s"],
    );
    if !scope.is_empty() {
        log_args.push("--".into());
        log_args.push(scope.clone());
    }
    let commits = match run_git(&log_args) {
        Ok(out) => parse_log(&out),
        Err(e) if e.message.contains("does not have any commits") => Vec::new(),
        Err(e) => return Err(map_run_err(e, "git log")),
    };

    Ok(GitSnapshot {
        status: "ok",
        error: None,
        git_root: Some(git_root.to_string_lossy().into_owned()),
        scope_rel: Some(scope),
        branch: parsed.branch,
        upstream: parsed.upstream,
        ahead: parsed.ahead,
        behind: parsed.behind,
        changes,
        staged,
        unique_count,
        commits,
        refreshed_at: now_ms(),
    })
}

fn with_args(base: &[String], extra: &[&str]) -> Vec<String> {
    let mut v = base.to_vec();
    v.extend(extra.iter().map(|s| s.to_string()));
    v
}

fn map_run_err(e: RunError, what: &str) -> SnapErr {
    if e.missing {
        SnapErr::GitMissing
    } else if e.message.contains("not a git repository") {
        SnapErr::NonGit
    } else {
        SnapErr::Error(format!("{what}: {e}", e = e.message))
    }
}

fn snapshot_error(status: &'static str, error: Option<String>) -> GitSnapshot {
    GitSnapshot {
        status,
        error,
        git_root: None,
        scope_rel: None,
        branch: None,
        upstream: None,
        ahead: None,
        behind: None,
        changes: Vec::new(),
        staged: Vec::new(),
        unique_count: 0,
        commits: Vec::new(),
        refreshed_at: now_ms(),
    }
}

fn snapshot(project: &Path) -> GitSnapshot {
    match snapshot_inner(project) {
        Ok(s) => s,
        Err(SnapErr::GitMissing) => snapshot_error("gitMissing", None),
        Err(SnapErr::NonGit) => snapshot_error("nonGit", None),
        Err(SnapErr::Error(msg)) => snapshot_error("error", Some(msg)),
    }
}

// ---------------------------------------------------------------------------
// Commands.

/// Full runtime git state for one project (§20: runtime truth, the
/// frontend never persists it). Never rejects — every failure folds into
/// `status` so the panel can render §152/§153 messages.
///
/// ASYNC on purpose: sync commands execute on the native main thread, and
/// this handler spawns git.exe processes (0.1–2 s). The Phase 9 watcher
/// calls it on every fs-event batch — sustained writes saturated the main
/// thread and the window stopped pumping messages (0.7.0 startup freeze,
/// owner 2026-10-11; lessons L35). Async commands run on the runtime.
#[tauri::command]
pub async fn git_snapshot(root_path: String) -> GitSnapshot {
    tauri::async_runtime::spawn_blocking(move || snapshot(Path::new(&root_path)))
        .await
        .unwrap_or_else(|err| GitSnapshot {
            status: "error",
            error: Some(format!("git task failed: {err}")),
            git_root: None,
            scope_rel: None,
            branch: None,
            upstream: None,
            ahead: None,
            behind: None,
            changes: Vec::new(),
            staged: Vec::new(),
            unique_count: 0,
            commits: Vec::new(),
            refreshed_at: 0,
        })
}

/// Component-wise rel validation: no `..`, no absolute/drive forms, no
/// pathspec magic (`:...`). The file itself may not exist (staged
/// deletions), so canonicalize is not an option here — but a pathspec
/// after `--` with these rules cannot escape the project scope.
fn sanitize_rel(rel: &str) -> Result<String, String> {
    let rel = rel.trim().replace('\\', "/");
    if rel.is_empty() || rel.starts_with(':') {
        return Err("Invalid path.".into());
    }
    let mut parts: Vec<&str> = Vec::new();
    for comp in rel.split('/') {
        match comp {
            "" | "." => continue,
            ".." => return Err("Path escapes the project root.".into()),
            c if c.contains(':') => return Err("Invalid path.".into()),
            c => parts.push(c),
        }
    }
    if parts.is_empty() {
        return Err("Invalid path.".into());
    }
    Ok(parts.join("/"))
}

#[tauri::command]
pub async fn git_diff(
    root_path: String,
    rel: String,
    staged: bool,
    commit_hash: Option<String>,
) -> Result<GitDiffResult, String> {
    // ASYNC on purpose (L35 family, Phase 10 audit): this handler spawns
    // git.exe; a sync command would run it on the native main thread and a
    // slow repo could freeze the window for up to the 10 s timeout per click.
    tauri::async_runtime::spawn_blocking(move || {
        diff_inner(root_path, rel, staged, commit_hash)
    })
    .await
    .map_err(|e| format!("git diff task failed: {e}"))?
}

fn diff_inner(
    root_path: String,
    rel: String,
    staged: bool,
    commit_hash: Option<String>,
) -> Result<GitDiffResult, String> {
    let project = dunce::canonicalize(&root_path)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;
    let root_out = run_git(&with_args(
        &git_base_args(&project),
        &["rev-parse", "--show-toplevel"],
    ))
    .map_err(|e| run_err_string(e, "detect git root"))?;
    let git_root = PathBuf::from(root_out.trim());
    let scope = scope_of(&project, &git_root)
        .map_err(|e| run_err_string(RunError::msg(e), "detect git root"))?;
    let rel = sanitize_rel(&rel)?;
    // :(literal) magic disables glob/pathspec interpretation — a file
    // literally named a*b.py must match only itself, not aXb.py
    // (spec-012 L-r3). sanitize_rel already rejects ':' inside components.
    let joined = if scope.is_empty() { rel } else { format!("{scope}/{rel}") };
    let pathspec = format!(":(literal){joined}");

    let argv = match commit_hash {
        Some(hash) => show_diff_argv(&git_root, &sanitize_hash(&hash)?, &pathspec),
        None => diff_argv(&git_root, &pathspec, staged),
    };
    let out = run_git_capped(&argv, DIFF_MAX_BYTES, DIFF_MAX_LINES)
        .map_err(|e| run_err_string(e, "git diff"))?;
    Ok(GitDiffResult {
        text: out.text,
        truncated: out.truncated,
        lines: out.lines as u32,
    })
}

/// A commit-scoped diff shows that file's change INSIDE the given commit
/// (`git show --format=` drops the log header, keeps the diff — and works
/// for root commits where `hash^` does not exist). §70 applies to EVERY
/// patch-producing invocation: `git show` emits patches, so the same
/// --no-ext-diff/--no-textconv fence as diff_argv (Phase 10 audit —
/// without them a repo's diff.external / GIT_EXTERNAL_DIFF config would
/// launch an external program through us).
fn show_diff_argv(root: &Path, hash: &str, pathspec: &str) -> Vec<String> {
    let mut args = git_base_args(root);
    args.push("show".into());
    args.push("--format=".into());
    // Merge commits default to a COMBINED diff (@@@ hunks, double-prefixed
    // lines) that the frontend's unified parser cannot read; --first-parent
    // keeps every commit's patch in plain unified form (spec-012 M2/D2).
    args.push("--first-parent".into());
    args.push("--no-ext-diff".into());
    args.push("--no-textconv".into());
    args.push(hash.into());
    args.push("--".into());
    args.push(pathspec.into());
    args
}

/// Revisions crossing the bridge must be plain hex (4–40 chars) — anything
/// else (`HEAD~2^{…}`, ranges) is rev syntax we never meant to allow.
fn sanitize_hash(hash: &str) -> Result<String, String> {
    let h = hash.trim();
    let ok = (4..=40).contains(&h.len()) && h.bytes().all(|b| b.is_ascii_hexdigit());
    if ok {
        Ok(h.to_ascii_lowercase())
    } else {
        Err("Invalid commit id.".into())
    }
}

// ---------------------------------------------------------------------------
// Commit detail (owner 2026-10-10: clicking a Recent Commit must open the
// commit's information — author/date/message plus the files it touched).

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct GitCommitFile {
    pub rel: String,
    pub letter: char,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub orig_rel: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GitCommitDetail {
    pub hash: String,
    pub author: String,
    /// ISO-8601 author date as git prints it (%aI).
    pub date: String,
    pub message: String,
    pub files: Vec<GitCommitFile>,
}

/// `git show --name-status --format=<unit-separated>` — one header block,
/// then one `XY\tpath` line per touched file (renames carry the old path).
///
/// The format string terminates the header with a `\x1e` record separator
/// (spec-012 H1/D5): `%B` is the RAW multiline body, so without a hard
/// boundary every body line fell into the name-status loop — the message
/// showed only its first line, and body lines containing a TAB manufactured
/// phantom file entries. Cut on the LAST `\x1e`: a pathological message
/// body containing a raw `\x1e` can only appear before the real sentinel.
fn parse_commit_detail(out: &str, scope: &str) -> Option<GitCommitDetail> {
    let (header_block, files_block) = out.rsplit_once('\u{1e}')?;
    let mut header_lines = header_block.lines();
    let first = header_lines.next()?;
    let mut parts = first.splitn(4, '\u{1f}');
    let hash = parts.next()?.to_string();
    let author = parts.next()?.to_string();
    let date = parts.next()?.to_string();
    let mut message = parts.next().unwrap_or_default().to_string();
    for line in header_lines {
        message.push('\n');
        message.push_str(line);
    }
    let message = message.trim_end().to_string();

    let mut files = Vec::new();
    for line in files_block.lines() {
        if line.is_empty() {
            continue;
        }
        // R100<TAB>old<TAB>new / M<TAB>path — split on tabs, last is new.
        // Status tokens are alphanumeric (M/A/D/R100/C99/T); anything else
        // is not a name-status line.
        let tabs: Vec<&str> = line.split('\t').collect();
        let (status, path, orig) = match tabs.as_slice() {
            [st, old, new] if is_status_token(st) => (st, *new, Some(old.to_string())),
            [st, p] if is_status_token(st) => (st, *p, None),
            _ => continue,
        };
        let letter = status.chars().next().unwrap_or('M');
        if !in_scope(path, scope) {
            continue;
        }
        let rel = to_project_rel(path, scope);
        let orig_rel = orig
            .filter(|o| in_scope(o, scope))
            .map(|o| to_project_rel(&o, scope));
        files.push(GitCommitFile { rel, letter, orig_rel });
    }
    Some(GitCommitDetail { hash, author, date, message, files })
}

fn is_status_token(s: &str) -> bool {
    !s.is_empty() && s.chars().all(|c| c.is_ascii_alphanumeric())
}

#[tauri::command]
pub async fn git_commit_detail(root_path: String, hash: String) -> Result<GitCommitDetail, String> {
    // ASYNC for the same reason as git_diff (L35 family, Phase 10 audit).
    tauri::async_runtime::spawn_blocking(move || commit_detail_inner(root_path, hash))
        .await
        .map_err(|e| format!("commit detail task failed: {e}"))?
}

fn commit_detail_inner(root_path: String, hash: String) -> Result<GitCommitDetail, String> {
    let project = dunce::canonicalize(&root_path)
        .map_err(|e| format!("Project folder is not accessible: {e}"))?;
    let root_out = run_git(&with_args(
        &git_base_args(&project),
        &["rev-parse", "--show-toplevel"],
    ))
    .map_err(|e| run_err_string(e, "detect git root"))?;
    let git_root = PathBuf::from(root_out.trim());
    let scope = scope_of(&project, &git_root)
        .map_err(|e| run_err_string(RunError::msg(e), "detect git root"))?;
    let hash = sanitize_hash(&hash)?;

    let out = run_git(&with_args(
        &git_base_args(&git_root),
        &[
            "show",
            "--name-status",
            // Merge commits: diff/file list against the FIRST parent only
            // (spec-012 M2/D2, VS Code's default view). For regular commits
            // --first-parent is a no-op.
            "--first-parent",
            "--no-ext-diff",
            "--no-textconv",
            // %B is the raw multiline body; %x1e terminates the header so
            // parse_commit_detail has a hard boundary (spec-012 H1/D5).
            "--format=%H%x1f%an%x1f%aI%x1f%B%x1e",
            &hash,
        ],
    ))
    .map_err(|e| run_err_string(e, "read commit"))?;
    parse_commit_detail(&out, &scope)
        .ok_or_else(|| "Could not read commit details.".into())
}

/// Both git_diff and git_commit_detail reject with a plain user-facing
/// message (§153 wording for a missing git; otherwise the what+stderr from
/// the runner). `what` names the operation — commit-detail failures used
/// to read "git diff failed." (spec-012 L-r6).
fn run_err_string(e: RunError, what: &str) -> String {
    if e.missing {
        "Git is not installed or cannot be found.".into()
    } else if e.message.is_empty() {
        format!("{what} failed.")
    } else {
        e.message
    }
}

// ---------------------------------------------------------------------------
// Tests — real temp repositories wherever output FORMAT matters (the
// parser's assumptions are only provable against real git output).

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn sh(dir: &Path, args: &[&str]) {
        let out = Command::new("git")
            .arg("-C")
            .arg(dir)
            .args(args)
            .output()
            .expect("spawn git");
        assert!(
            out.status.success(),
            "git {:?} failed: {}",
            args,
            String::from_utf8_lossy(&out.stderr)
        );
    }

    fn init_repo(dir: &Path) {
        std::fs::create_dir_all(dir).unwrap();
        sh(dir, &["init", "-q", "-b", "main"]);
        sh(dir, &["config", "user.email", "t@example.com"]);
        sh(dir, &["config", "user.name", "T"]);
    }

    fn write_file(dir: &Path, rel: &str, content: &str) {
        let p = dir.join(rel.replace('/', "\\"));
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(p, content).unwrap();
    }

    fn commit_all(dir: &Path, msg: &str) {
        sh(dir, &["add", "-A"]);
        sh(dir, &["commit", "-q", "-m", msg]);
    }

    fn status_text(dir: &Path) -> String {
        run_git(&with_args(
            &git_base_args(dir),
            &["status", "--porcelain=v2", "--branch"],
        ))
        .expect("git status")
    }

    // ---- pure parser (V1) ----

    #[test]
    fn parse_headers_letters_untracked_unmerged() {
        let out = "# branch.oid 1234\n\
                   # branch.head main\n\
                   # branch.upstream origin/main\n\
                   # branch.ab +2 -1\n\
                   1 .M N... 100644 100644 100644 h1 h2 file with space.txt\n\
                   1 M. N... 100644 100644 100644 h1 h2 staged.txt\n\
                   1 MM N... 100644 100644 100644 h1 h2 both.txt\n\
                   1 D. N... 100644 100644 100644 h1 h2 gone staged.txt\n\
                   ? untracked.txt\n\
                   u UU N... 100644 100644 100644 100644 h1 h2 h3 conf.txt\n";
        let p = parse_status_output(out);
        assert_eq!(p.branch.as_deref(), Some("main"));
        assert_eq!(p.upstream.as_deref(), Some("origin/main"));
        assert_eq!(p.ahead, Some(2));
        assert_eq!(p.behind, Some(1));
        let find = |path: &str| {
            p.entries.iter().find(|e| e.path == path).cloned().unwrap()
        };
        let e = find("file with space.txt");
        assert_eq!(e.staged_letter, None);
        assert_eq!(e.worktree_letter, Some('M'));
        let e = find("staged.txt");
        assert_eq!(e.staged_letter, Some('M'));
        assert_eq!(e.worktree_letter, None);
        let e = find("both.txt");
        assert_eq!(e.staged_letter, Some('M'));
        assert_eq!(e.worktree_letter, Some('M'));
        let e = find("gone staged.txt");
        assert_eq!(e.staged_letter, Some('D'));
        assert_eq!(e.worktree_letter, None);
        let e = find("untracked.txt");
        assert_eq!(e.staged_letter, None);
        assert_eq!(e.worktree_letter, Some('?'));
        let e = find("conf.txt");
        assert_eq!(e.staged_letter, Some('U'));
        assert_eq!(e.worktree_letter, Some('U'));
    }

    #[test]
    fn scope_filter_unique_and_project_rel() {
        let entries = vec![
            RawEntry { path: "apps/viewer/a.ts".into(), orig_path: None,
                staged_letter: None, worktree_letter: Some('M') },
            RawEntry { path: "apps/viewer/sub/deep.py".into(), orig_path: None,
                staged_letter: Some('A'), worktree_letter: None },
            RawEntry { path: "apps/backend/b.ts".into(), orig_path: None,
                staged_letter: None, worktree_letter: Some('M') },
            RawEntry { path: "packages/c.ts".into(), orig_path: None,
                staged_letter: None, worktree_letter: Some('M') },
        ];
        let (changes, staged, unique) = scoped_groups(&entries, "apps/viewer");
        assert_eq!(changes.len(), 1);
        assert_eq!(changes[0].rel, "a.ts");
        assert_eq!(staged.len(), 1);
        assert_eq!(staged[0].rel, "sub/deep.py");
        assert_eq!(unique, 2);
    }

    #[test]
    fn same_file_two_groups_badge_once() {
        let entries = vec![RawEntry { path: "cfg.yaml".into(), orig_path: None,
            staged_letter: Some('M'), worktree_letter: Some('M') }];
        let (changes, staged, unique) = scoped_groups(&entries, "");
        assert_eq!(changes.len(), 1);
        assert_eq!(staged.len(), 1);
        assert_eq!(unique, 1);
    }

    #[test]
    fn sanitize_rel_rules() {
        assert!(sanitize_rel("..").is_err());
        assert!(sanitize_rel("a/../../b").is_err());
        assert!(sanitize_rel(":glob-magic").is_err());
        assert!(sanitize_rel("C:/x").is_err());
        assert!(sanitize_rel("").is_err());
        assert_eq!(sanitize_rel("src/./a.ts").unwrap(), "src/a.ts");
        assert_eq!(sanitize_rel("src\\a.ts").unwrap(), "src/a.ts");
    }

    #[test]
    fn diff_argv_carries_safe_flags() {
        let argv = diff_argv(Path::new("R"), "apps/viewer/a.ts", true);
        let joined = argv.join(" ");
        assert!(joined.contains("--no-pager"));
        assert!(joined.contains("-c core.quotepath=false"));
        assert!(joined.contains("--no-ext-diff"));
        assert!(joined.contains("--no-textconv"));
        assert!(joined.contains("--cached"));
        assert!(joined.ends_with("-- apps/viewer/a.ts"));
    }

    /// Phase 10 audit (§70): the commit-scoped `git show` emits patches, so
    /// it must carry the same external-diff/textconv fences as diff_argv.
    #[test]
    fn show_diff_argv_carries_safe_flags() {
        let argv = show_diff_argv(Path::new("R"), "ab12", "apps/viewer/a.ts");
        let joined = argv.join(" ");
        assert!(joined.contains("--no-ext-diff"));
        assert!(joined.contains("--no-textconv"));
        assert!(joined.contains("show"));
        assert!(joined.ends_with("-- apps/viewer/a.ts"));
        // The hash stays a bare token after `--format=` — never rev syntax.
        assert!(argv.contains(&"ab12".to_string()));
        // Merge patches stay unified (never combined @@@) — spec-012 M2/D2.
        assert!(joined.contains("--first-parent"));
    }

    // ---- real repositories (format truth + §174 scenario) ----

    #[test]
    fn real_repo_rename_format_and_snapshot() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "old.txt", "one\n");
        commit_all(repo, "c1");
        sh(repo, &["mv", "old.txt", "new.txt"]);

        let snap = snapshot(repo);
        assert_eq!(snap.status, "ok");
        assert_eq!(snap.scope_rel.as_deref(), Some(""));
        assert_eq!(snap.staged.len(), 1);
        assert_eq!(snap.staged[0].letter, 'R');
        assert_eq!(snap.staged[0].rel, "new.txt");
        assert_eq!(snap.staged[0].orig_rel.as_deref(), Some("old.txt"));
        assert_eq!(snap.unique_count, 1);
    }

    #[test]
    fn real_subdirectory_scope_174() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "apps/viewer/a.ts", "1\n");
        write_file(repo, "apps/backend/b.ts", "1\n");
        write_file(repo, "packages/c.ts", "1\n");
        commit_all(repo, "seed");
        // Scoped commit vs unscoped commit.
        write_file(repo, "apps/viewer/a.ts", "2\n");
        commit_all(repo, "viewer change");
        write_file(repo, "apps/backend/b.ts", "2\n");
        commit_all(repo, "backend change");
        // Working-tree changes across scopes + one staged + one untracked.
        write_file(repo, "apps/viewer/a.ts", "3\n");
        write_file(repo, "apps/backend/b.ts", "3\n");
        write_file(repo, "packages/c.ts", "3\n");
        write_file(repo, "apps/viewer/staged.ts", "s\n");
        sh(repo, &["add", "apps/viewer/staged.ts"]);
        write_file(repo, "apps/viewer/untracked.ts", "u\n");

        let viewer = repo.join("apps").join("viewer");
        let snap = snapshot(&viewer);
        assert_eq!(snap.status, "ok");
        assert_eq!(snap.scope_rel.as_deref(), Some("apps/viewer"));
        // Badge: a.ts + staged.ts + untracked.ts = 3 unique (backend/packages excluded).
        assert_eq!(snap.unique_count, 3);
        let rels: Vec<&str> = snap.changes.iter().map(|e| e.rel.as_str()).collect();
        assert!(rels.contains(&"a.ts"));
        assert!(rels.contains(&"untracked.ts"));
        assert!(!rels.iter().any(|r| r.contains("backend") || r.contains("packages")));
        assert_eq!(snap.staged.len(), 1);
        assert_eq!(snap.staged[0].rel, "staged.ts");
        // Branch is repository-wide (§63); scoped log (§64).
        assert_eq!(snap.branch.as_deref(), Some("main"));
        assert!(snap.commits.iter().all(|c| c.subject.contains("viewer") || c.subject == "seed"));
        assert!(snap.commits.iter().any(|c| c.subject == "viewer change"));
        assert!(!snap.commits.iter().any(|c| c.subject == "backend change"));
    }

    #[test]
    fn real_ahead_behind_via_clone() {
        let tmp = TempDir::new().unwrap();
        let bare = tmp.path().join("origin.git");
        std::fs::create_dir_all(&bare).unwrap();
        sh(&bare, &["init", "-q", "--bare", "-b", "main"]);
        let a = tmp.path().join("a");
        sh(tmp.path(), &["clone", "-q", "--no-hardlinks", bare.to_str().unwrap(), a.to_str().unwrap()]);
        init_repo(&a); // config only (clone has no identity)
        write_file(&a, "f.txt", "1\n");
        commit_all(&a, "c1");
        sh(&a, &["push", "-q"]);
        // A second clone pushes a commit A does not have.
        let b = tmp.path().join("b");
        sh(tmp.path(), &["clone", "-q", "--no-hardlinks", bare.to_str().unwrap(), b.to_str().unwrap()]);
        write_file(&b, "f.txt", "2\n");
        commit_all(&b, "c2");
        sh(&b, &["push", "-q"]);
        // Local commit in A → ahead; fetch → sees the remote one → behind.
        write_file(&a, "local.txt", "x\n");
        commit_all(&a, "local");
        sh(&a, &["fetch", "-q"]);

        let snap = snapshot(&a);
        assert_eq!(snap.status, "ok");
        assert_eq!(snap.upstream.as_deref(), Some("origin/main"));
        assert_eq!(snap.ahead, Some(1));
        assert_eq!(snap.behind, Some(1));
    }

    #[test]
    fn real_conflict_marks_u_both_groups() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "f.txt", "base\n");
        commit_all(repo, "base");
        sh(repo, &["checkout", "-q", "-b", "feat"]);
        write_file(repo, "f.txt", "feat\n");
        commit_all(repo, "feat change");
        sh(repo, &["checkout", "-q", "main"]);
        write_file(repo, "f.txt", "main\n");
        commit_all(repo, "main change");
        let merge = Command::new("git")
            .args(["-C", repo.to_str().unwrap(), "merge", "feat"])
            .output()
            .unwrap();
        assert!(!merge.status.success(), "merge should conflict");

        let snap = snapshot(repo);
        assert_eq!(snap.status, "ok");
        assert!(snap.changes.iter().any(|e| e.rel == "f.txt" && e.letter == 'U'));
        assert!(snap.staged.iter().any(|e| e.rel == "f.txt" && e.letter == 'U'));
        assert_eq!(snap.unique_count, 1);
    }

    #[test]
    fn real_diff_working_tree_and_staged() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "a.txt", "one\ntwo\n");
        commit_all(repo, "c1");
        write_file(repo, "a.txt", "one\nTWO\nthree\n");
        write_file(repo, "b.txt", "staged content\n");
        sh(repo, &["add", "b.txt"]);

        let wt = diff_inner(repo.to_string_lossy().into_owned(), "a.txt".into(), false, None).unwrap();
        assert!(!wt.truncated);
        assert!(wt.text.contains("-two"));
        assert!(wt.text.contains("+TWO"));
        assert!(wt.text.contains("+three"));

        let st = diff_inner(repo.to_string_lossy().into_owned(), "b.txt".into(), true, None).unwrap();
        assert!(st.text.contains("+staged content"));
        assert!(st.text.contains("new file"));

        // Path escape is refused before any git spawn.
        assert!(diff_inner(repo.to_string_lossy().into_owned(), "../x".into(), false, None).is_err());
        // Commit-scoped diff: the file's change inside one commit (works
        // for the root commit too, where hash^ does not exist).
        let head = run_git(&with_args(&git_base_args(repo), &["rev-parse", "--short", "HEAD"]))
            .unwrap();
        let cd = diff_inner(repo.to_string_lossy().into_owned(), "a.txt".into(), false, Some(head.trim().to_string())).unwrap();
        assert!(cd.text.contains("+one"));
        assert!(cd.text.contains("+two"));
        assert!(cd.text.contains("new file"));
        assert!(diff_inner(repo.to_string_lossy().into_owned(), "a.txt".into(), false, Some("HEAD~1^{tree}".into())).is_err());
    }

    #[test]
    fn real_diff_size_guard_truncates() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        let base: String = (0..30_000).map(|i| format!("line {i}\n")).collect();
        write_file(repo, "big.txt", &base);
        commit_all(repo, "big");
        let changed: String = (0..30_000).map(|i| format!("changed {i}\n")).collect();
        write_file(repo, "big.txt", &changed);

        let d = diff_inner(repo.to_string_lossy().into_owned(), "big.txt".into(), false, None).unwrap();
        assert!(d.truncated);
        assert!(d.lines <= DIFF_MAX_LINES as u32);
        assert!(d.text.len() <= DIFF_MAX_BYTES + 8);
    }

    #[test]
    fn real_empty_repo_and_detached() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        let snap = snapshot(repo);
        assert_eq!(snap.status, "ok");
        assert!(snap.commits.is_empty());
        assert_eq!(snap.branch.as_deref(), Some("main"));
        assert_eq!(snap.upstream, None);
        assert_eq!(snap.ahead, None);

        write_file(repo, "f.txt", "1\n");
        commit_all(repo, "c1");
        sh(repo, &["checkout", "-q", "--detach"]);
        let snap = snapshot(repo);
        assert_eq!(snap.branch.as_deref(), Some("(detached)"));
        assert_eq!(snap.upstream, None);
    }

    #[test]
    fn non_git_folder_is_nonGit() {
        let tmp = TempDir::new().unwrap();
        std::fs::create_dir_all(tmp.path().join("plain")).unwrap();
        let snap = snapshot(&tmp.path().join("plain"));
        assert_eq!(snap.status, "nonGit");
    }

    #[test]
    fn real_commit_detail_and_log_author() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "a.txt", "alpha
bravo
charlie
delta
");
        write_file(repo, "sub/b.txt", "1
");
        write_file(repo, "sub/keep.txt", "k
");
        commit_all(repo, "first commit");
        // modify ONE word of four lines: similarity stays high enough for
        // git to detect the later mv as a rename (R), not A+D.
        write_file(repo, "a.txt", "alpha
bravo
charlie
DELTA
");
        sh(repo, &["rm", "sub/b.txt"]);
        sh(repo, &["mv", "a.txt", "renamed.txt"]);
        write_file(repo, "new.txt", "n
");
        commit_all(repo, "second commit");

        let head = run_git(&with_args(&git_base_args(repo), &["rev-parse", "HEAD"])).unwrap();
        let d = commit_detail_inner(
            repo.to_string_lossy().into_owned(),
            head.trim().to_string(),
        )
        .unwrap();
        assert_eq!(d.author, "T");
        assert_eq!(d.message.trim(), "second commit");
        assert!(d.date.contains('T') && d.date.len() >= 20, "date={}", d.date);
        let find = |rel: &str| d.files.iter().find(|f| f.rel == rel).cloned().unwrap();
        assert_eq!(find("renamed.txt").letter, 'R');
        assert_eq!(find("renamed.txt").orig_rel.as_deref(), Some("a.txt"));
        assert_eq!(find("sub/b.txt").letter, 'D');
        assert_eq!(find("new.txt").letter, 'A');

        // Log rows carry the author and a MILLISECOND ts.
        let snap = snapshot(repo);
        let c = snap.commits.first().unwrap();
        assert_eq!(c.author, "T");
        assert!(c.ts > 1_000_000_000_000, "ts={}", c.ts);

        // Subdirectory scope filters the file list (keep.txt untouched,
        // b.txt deleted — only b.txt is in scope for sub/).
        let d2 = commit_detail_inner(
            repo.join("sub").to_string_lossy().into_owned(),
            head.trim().to_string(),
        )
        .unwrap();
        assert_eq!(d2.files.len(), 1);
        assert_eq!(d2.files[0].rel, "b.txt");

        assert!(commit_detail_inner(repo.to_string_lossy().into_owned(), "zz~1".into()).is_err());
    }

    // ---- spec-012 G1/G2 (code review 2026-10-11) ----

    /// H1: %B is the raw multiline body; header/file boundary is the %x1e
    /// sentinel, and body lines that LOOK like name-status entries
    /// (single TAB, "M<TAB>path") must stay in the message.
    #[test]
    fn real_commit_detail_multiline_message_body() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "a.txt", "1\n");
        commit_all(repo, "single");
        write_file(repo, "a.txt", "2\n");
        write_file(repo, "b.txt", "b\n");
        sh(repo, &["add", "-A"]);
        // --cleanup=verbatim: default cleanup strips the whitespace-only
        // line we deliberately planted in the body.
        sh(
            repo,
            &[
                "commit",
                "-q",
                "--cleanup=verbatim",
                "-m",
                "subject line\n\nbody para one\n\t\nM\tlooks_like_a_file.txt\nreal body end",
            ],
        );

        let head = run_git(&with_args(&git_base_args(repo), &["rev-parse", "HEAD"])).unwrap();
        let d = commit_detail_inner(
            repo.to_string_lossy().into_owned(),
            head.trim().to_string(),
        )
        .unwrap();
        assert_eq!(
            d.message,
            "subject line\n\nbody para one\n\t\nM\tlooks_like_a_file.txt\nreal body end"
        );
        let rels: Vec<&str> = d.files.iter().map(|f| f.rel.as_str()).collect();
        assert_eq!(rels, ["a.txt", "b.txt"], "phantom file entries leaked from message body");
    }

    /// M2: merge commits show first-parent unified diffs and a real
    /// name-status file list (never the combined @@@ format).
    #[test]
    fn real_merge_commit_first_parent_view() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "base.txt", "base\n");
        commit_all(repo, "base");
        sh(repo, &["checkout", "-q", "-b", "feat"]);
        write_file(repo, "feat.txt", "feat content\n");
        commit_all(repo, "feat adds file");
        sh(repo, &["checkout", "-q", "main"]);
        write_file(repo, "main.txt", "main content\n");
        commit_all(repo, "main adds file");
        sh(repo, &["merge", "-q", "--no-edit", "feat"]);
        let head = run_git(&with_args(&git_base_args(repo), &["rev-parse", "HEAD"])).unwrap();
        let hash = head.trim().to_string();
        let root = repo.to_string_lossy().into_owned();

        let d = commit_detail_inner(root.clone(), hash.clone()).unwrap();
        let rels: Vec<String> = d.files.iter().map(|f| f.rel.clone()).collect();
        assert!(rels.contains(&"feat.txt".to_string()), "merge file list empty: {rels:?}");
        assert!(d.message.contains("Merge"), "message={}", d.message);

        let diff = diff_inner(root, "feat.txt".into(), false, Some(hash)).unwrap();
        assert!(diff.text.contains("@@"), "no unified hunks: {}", diff.text);
        assert!(!diff.text.contains("@@@"), "combined diff leaked: {}", diff.text);
        assert!(diff.text.contains("+feat content"));
    }

    /// L-r2: full C-quote escape set incl. `\a\b\f\v` and octal `\ooo`.
    #[test]
    fn unquote_full_c_escape_set() {
        assert_eq!(unquote("plain.txt"), "plain.txt");
        assert_eq!(unquote("\"no escapes\""), "no escapes");
        assert_eq!(unquote("\"a\\tb\""), "a\tb");
        assert_eq!(unquote("\"a\\ab\\bc\\fd\\ve\""), "a\u{7}b\u{8}c\u{c}d\u{b}e");
        assert_eq!(unquote("\"\\007\\040x\""), "\u{7} x");
        assert_eq!(unquote("\"quote\\\"and\\\\slash\""), "quote\"and\\slash");
        // No closing quote → returned unmodified.
        assert_eq!(unquote("\"end\\"), "\"end\\");
    }

    /// L-r3: `:(literal)` keeps glob metachars in filenames literal. `*` is
    /// not legal in Windows filenames, so the probe uses `[xy]` (a legal
    /// name that, unquoted, also matches axb.py).
    #[test]
    fn real_diff_literal_pathspec_bracket_filename() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        write_file(repo, "plain.txt", "seed\n");
        commit_all(repo, "seed");
        write_file(repo, "a[xy]b.py", "brackets are literal\n");
        write_file(repo, "axb.py", "would match the glob\n");
        sh(repo, &["add", "-A"]);

        let d = diff_inner(
            repo.to_string_lossy().into_owned(),
            "a[xy]b.py".into(),
            true,
            None,
        )
        .unwrap();
        assert!(d.text.contains("a[xy]b.py"), "text={}", d.text);
        assert!(!d.text.contains("axb.py"), "glob matched an unrelated file: {}", d.text);
    }

    /// L-r6: the empty-message fallback names the failing operation.
    #[test]
    fn run_err_string_names_the_operation() {
        let empty = RunError { missing: false, timeout: false, message: String::new() };
        assert!(run_err_string(empty, "read commit").contains("commit"));
        let missing = RunError { missing: true, timeout: false, message: String::new() };
        assert_eq!(
            run_err_string(missing, "git diff"),
            "Git is not installed or cannot be found."
        );
    }

    /// L-r1: the project root itself as a git entry must resolve to ".",
    /// never slice past the end of the path.
    #[test]
    fn to_project_rel_scope_equal_path_is_dot() {
        assert_eq!(to_project_rel("apps/viewer", "apps/viewer"), ".");
        assert_eq!(to_project_rel("apps/viewer/a.ts", "apps/viewer"), "a.ts");
        assert_eq!(to_project_rel("a.ts", ""), "a.ts");
    }

    /// M6: thousands of per-file warnings on stderr while git still exits 0
    /// used to fill the undrained pipe and stall the child until the 10 s
    /// timeout misfired. autocrlf=true makes `git add` emit one
    /// "LF will be replaced by CRLF" warning per LF file.
    #[test]
    fn real_git_stderr_flood_does_not_time_out() {
        let tmp = TempDir::new().unwrap();
        let repo = tmp.path();
        init_repo(repo);
        sh(repo, &["config", "core.autocrlf", "true"]);
        for i in 0..1500 {
            write_file(repo, &format!("f{i:04}.txt"), "lf only\n");
        }
        let out = run_git(&with_args(&git_base_args(repo), &["add", "-A"]));
        assert!(out.is_ok(), "stderr flood must not fail the call: {out:?}");
    }
}
