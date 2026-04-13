import { describe, expect, it } from "vitest";
import { formatCredits, formatMoney2, formatSignedMoney2 } from "./formatCredits";

describe("formatCredits", () => {
  it("formats positive with thousands and two decimals", () => {
    expect(formatCredits("6410.00000000")).toEqual({ display: "6,410.00", isNegative: false });
  });

  it("formats negative with space before minus and two decimals", () => {
    expect(formatCredits("-6410.00000000")).toEqual({ display: " -6,410.00", isNegative: true });
  });

  it("treats zero as non-negative", () => {
    expect(formatCredits("0")).toEqual({ display: "0.00", isNegative: false });
  });

  it("handles null and empty", () => {
    expect(formatCredits(null)).toEqual({ display: "—", isNegative: false });
    expect(formatCredits(undefined)).toEqual({ display: "—", isNegative: false });
    expect(formatCredits("   ")).toEqual({ display: "—", isNegative: false });
  });

  it("strips thousand commas in input", () => {
    expect(formatCredits("-6,410.12")).toEqual({ display: " -6,410.12", isNegative: true });
  });
});

describe("formatMoney2", () => {
  it("rounds to two fraction digits", () => {
    expect(formatMoney2("127.00000000")).toBe("127.00");
    expect(formatMoney2("-3.456")).toBe("-3.46");
  });
});

describe("formatSignedMoney2", () => {
  it("adds explicit sign and two decimals", () => {
    expect(formatSignedMoney2("127.00000000")).toBe("+127.00");
    expect(formatSignedMoney2("-10.5")).toBe("-10.50");
    expect(formatSignedMoney2("0")).toBe("0.00");
  });
});
