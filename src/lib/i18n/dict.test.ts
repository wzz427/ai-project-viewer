import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { en, zh, relativeTimeDict, translate } from "./dict";
import { RUST_ERROR_ANCHORS, translateRustError } from "./rustErrors";

describe("i18n dictionary (spec-016)", () => {
  it("en and zh carry the exact same key set", () => {
    expect(Object.keys(zh).sort()).toEqual(Object.keys(en).sort());
  });

  it("no empty values in either locale", () => {
    for (const [key, value] of Object.entries(en)) {
      expect(value.length, `en.${key}`).toBeGreaterThan(0);
    }
    for (const [key, value] of Object.entries(zh)) {
      expect(value.length, `zh.${key}`).toBeGreaterThan(0);
    }
  });

  it("interpolates {vars} and leaves unknown keys readable", () => {
    expect(translate("en", "toast.copied", { what: "绝对路径", text: '"C:\\a"' }))
      .toBe('Copied 绝对路径: "C:\\a"');
    expect(translate("zh", "toast.copied", { what: "绝对路径", text: '"C:\\a"' }))
      .toBe('已复制绝对路径:"C:\\a"');
  });

  it("relative time is locale-aware at the same instants", () => {
    const now = Date.parse("2026-10-26T12:00:00Z");
    const min = 60_000;
    expect(relativeTimeDict("en", now, now - 30 * min)).toBe("30m ago");
    expect(relativeTimeDict("zh", now, now - 30 * min)).toBe("30 分钟前");
    expect(relativeTimeDict("en", now, now - 30 * 60 * min)).toBe("yesterday");
    expect(relativeTimeDict("zh", now, now - 30 * 60 * min)).toBe("昨天");
  });
});

describe("rust error map drift guard (spec-016)", () => {
  // If this goes red, a Rust message was reworded: update the prefix/src
  // pair in rustErrors.ts (the Chinese wording must follow the English).
  it("every anchor still exists verbatim in the Rust sources", () => {
    const rustSources = ["handoff", "run", "file_inspect", "updater", "properties"]
      .map((m) =>
        readFileSync(join(process.cwd(), "src-tauri", "src", `${m}.rs`), "utf-8"),
      )
      .join("\n");
    for (const anchor of RUST_ERROR_ANCHORS) {
      expect(rustSources.includes(anchor), `missing anchor: ${anchor}`).toBe(true);
    }
  });

  it("translates exact and prefixed messages, passes unknowns through", () => {
    expect(translateRustError("No update staged.", "zh")).toBe("没有待安装的更新。");
    expect(translateRustError("Not found: docs/readme.md", "zh")).toBe(
      "未找到: docs/readme.md",
    );
    expect(translateRustError("Some brand new error", "zh")).toBe(
      "Some brand new error",
    );
    expect(translateRustError("No update staged.", "en")).toBe("No update staged.");
  });
});
