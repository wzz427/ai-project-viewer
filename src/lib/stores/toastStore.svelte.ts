export interface ToastItem {
  id: number;
  text: string;
  kind: "info" | "error";
}

let nextId = 1;
let autoHide: ReturnType<typeof setTimeout> | null = null;

/**
 * Single-slot toast: the shell only ever needs one message at a time,
 * a newer message replaces the older one.
 */
export const toastState = $state({
  current: null as ToastItem | null,
});

export function toast(
  text: string,
  opts: { kind?: "info" | "error"; timeoutMs?: number } = {},
) {
  toastState.current = {
    id: nextId++,
    text,
    kind: opts.kind ?? "info",
  };
  if (autoHide) clearTimeout(autoHide);
  autoHide = setTimeout(() => dismissToast(toastState.current?.id ?? 0), opts.timeoutMs ?? 4000);
}

export function dismissToast(id: number) {
  if (toastState.current?.id === id) {
    toastState.current = null;
  }
}
