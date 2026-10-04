import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import en from "../src/i18n/en.json" with { type: "json" };
import bn from "../src/i18n/bn.json" with { type: "json" };
import { toBanglaDigits, formatNumber, formatCurrency } from "../src/lib/format.ts";
import * as api from "../src/lib/api.ts";

describe("Task 8: Shared Components & Layout Verification", () => {
  test("Bangla numeral conversion works correctly", () => {
    assert.equal(toBanglaDigits("0123456789"), "০১২৩৪৫৬৭৮৯");
    assert.equal(toBanglaDigits("1,500"), "১,৫০০");
    assert.equal(toBanglaDigits("৳25,000"), "৳২৫,০০০");
  });

  test("formatNumber and formatCurrency work with English and Bangla", () => {
    assert.equal(formatNumber(1500, false), "1,500");
    assert.equal(formatNumber(1500, true), "১,৫০০");
    assert.equal(formatCurrency(1500, false), "৳1,500");
    assert.equal(formatCurrency(1500, true), "৳১,৫০০");
  });

  test("en.json and bn.json have matching key structures", () => {
    function getKeys(obj: any, prefix = ""): string[] {
      let keys: string[] = [];
      for (const k of Object.keys(obj)) {
        const full = prefix ? `${prefix}.${k}` : k;
        if (typeof obj[k] === "object" && obj[k] !== null && !Array.isArray(obj[k])) {
          keys = keys.concat(getKeys(obj[k], full));
        } else {
          keys.push(full);
        }
      }
      return keys.sort();
    }

    const enKeys = getKeys(en);
    const bnKeys = getKeys(bn);

    assert.deepEqual(
      enKeys,
      bnKeys,
      `i18n keys mismatch between en and bn:\nOnly in en: ${enKeys.filter((k) => !bnKeys.includes(k)).join(", ")}\nOnly in bn: ${bnKeys.filter((k) => !enKeys.includes(k)).join(", ")}`
    );

    // Check essential sections exist
    const essentialSections = [
      "nav",
      "common",
      "status",
      "home",
      "safe_range",
      "loan_check",
      "calendar",
      "path",
      "progress",
      "me",
      "consent",
      "admin",
      "footer",
    ];
    for (const sec of essentialSections) {
      assert.ok(enKeys.some((k) => k.startsWith(`${sec}.`)), `Missing section ${sec} in translations`);
    }
  });

  test("API client exports all 15 required client functions", () => {
    const requiredFunctions = [
      "getStatus",
      "getSafeRange",
      "postLoanCheck",
      "getCalendar",
      "getPath",
      "getProgress",
      "postConsent",
      "getAdminFunnel",
      "getAdminForecastQuality",
      "getAdminFairness",
      "getAdminConfig",
      "putAdminConfig",
      "postAdminKillSwitch",
      "getAdminAuditLog",
      "getHealth",
    ];

    for (const fn of requiredFunctions) {
      assert.equal(
        typeof (api as any)[fn],
        "function",
        `Expected api.${fn} to be exported as a function`
      );
    }
  });

  test("All required components exist on disk", () => {
    const componentFiles = [
      "Card.tsx",
      "Button.tsx",
      "StatusBadge.tsx",
      "CheckRow.tsx",
      "BottomNav.tsx",
      "Footer.tsx",
      "WhySheet.tsx",
      "LanguageToggle.tsx",
      "Skeleton.tsx",
      "ErrorState.tsx",
      "EmptyState.tsx",
      "NumberFormat.tsx",
    ];

    for (const file of componentFiles) {
      const fullPath = path.join(process.cwd(), "src/components", file);
      assert.ok(fs.existsSync(fullPath), `Expected component file ${file} to exist at ${fullPath}`);
    }
  });

  test("Both contexts exist on disk", () => {
    const contextFiles = ["LanguageContext.tsx", "ConsentContext.tsx"];

    for (const file of contextFiles) {
      const fullPath = path.join(process.cwd(), "src/contexts", file);
      assert.ok(fs.existsSync(fullPath), `Expected context file ${file} to exist at ${fullPath}`);
    }
  });
});
