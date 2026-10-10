/**
 * Single-slot centered error dialog (owner 2026-10-11: run failures must
 * be unmissable — "在窗口正中间弹出一个错误信息窗口,并且说清楚错误原因",
 * replacing the corner toast for action failures). One dialog at a time;
 * closing releases everything.
 */

export const errorDialog = $state({
  current: null as { title: string; message: string } | null,
});

export function showErrorDialog(title: string, message: string) {
  errorDialog.current = { title, message };
}

export function closeErrorDialog() {
  errorDialog.current = null;
}
