import { describe, expect, it } from "vitest";
import { identitiesWithoutTypePrefixes, identityWithoutTypePrefix } from "./identityDisplay";

describe("identityWithoutTypePrefix", () => {
  it("strips email prefix", () => {
    expect(identityWithoutTypePrefix("email:demo@safetalk.local")).toBe("demo@safetalk.local");
  });

  it("strips any type prefix before first colon", () => {
    expect(identityWithoutTypePrefix("telegram:12345")).toBe("12345");
  });

  it("returns as-is when no colon", () => {
    expect(identityWithoutTypePrefix("plain-only")).toBe("plain-only");
  });
});

describe("identitiesWithoutTypePrefixes", () => {
  it("joins formatted identities", () => {
    expect(identitiesWithoutTypePrefixes(["email:a@b.c", "email:d@e.f"])).toBe("a@b.c, d@e.f");
  });
});
