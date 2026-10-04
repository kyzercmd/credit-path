import { test, describe } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";

describe("Task 9: Customer Screens Verification", () => {
  const customerPages = [
    "src/app/home/page.tsx",
    "src/app/safe-range/page.tsx",
    "src/app/loan-check/page.tsx",
    "src/app/calendar/page.tsx",
    "src/app/path/page.tsx",
    "src/app/progress/page.tsx",
    "src/app/me/page.tsx",
    "src/app/consent/page.tsx",
  ];

  const customerComponents = [
    "src/components/WeeklyChart.tsx",
    "src/components/LoanSliders.tsx",
    "src/components/HeadsUpCard.tsx",
  ];

  test("All 8 customer pages exist on disk", () => {
    for (const pagePath of customerPages) {
      const fullPath = path.resolve(pagePath);
      assert.ok(fs.existsSync(fullPath), `Page missing: ${pagePath}`);
      const content = fs.readFileSync(fullPath, "utf-8");
      assert.ok(content.length > 200, `Page content too short: ${pagePath}`);
    }
  });

  test("All 3 customer components exist on disk", () => {
    for (const compPath of customerComponents) {
      const fullPath = path.resolve(compPath);
      assert.ok(fs.existsSync(fullPath), `Component missing: ${compPath}`);
      const content = fs.readFileSync(fullPath, "utf-8");
      assert.ok(content.length > 200, `Component content too short: ${compPath}`);
    }
  });

  test("Screens include disclaimers and why sheets", () => {
    const homeContent = fs.readFileSync(path.resolve("src/app/home/page.tsx"), "utf-8");
    assert.ok(homeContent.includes("WhySheet"), "Home page must include WhySheet");
    assert.ok(homeContent.includes("Footer"), "Home page must include Footer");

    const loanContent = fs.readFileSync(path.resolve("src/app/loan-check/page.tsx"), "utf-8");
    assert.ok(loanContent.includes("LoanSliders"), "LoanCheck must use LoanSliders");
    assert.ok(loanContent.includes("StatusBadge"), "LoanCheck must use StatusBadge");

    const calContent = fs.readFileSync(path.resolve("src/app/calendar/page.tsx"), "utf-8");
    assert.ok(calContent.includes("WeeklyChart"), "Calendar must use WeeklyChart");
    assert.ok(calContent.includes("HeadsUpCard"), "Calendar must use HeadsUpCard");

    const safeRangeContent = fs.readFileSync(path.resolve("src/app/safe-range/page.tsx"), "utf-8");
    assert.ok(safeRangeContent.includes("stressed"), "SafeRange must include stress test display");
    assert.ok(safeRangeContent.includes("WhySheet"), "SafeRange must include WhySheet");

    const pathContent = fs.readFileSync(path.resolve("src/app/path/page.tsx"), "utf-8");
    assert.ok(pathContent.includes("missing_items"), "Path page must handle missing items");

    const meContent = fs.readFileSync(path.resolve("src/app/me/page.tsx"), "utf-8");
    assert.ok(meContent.includes("LanguageToggle"), "Me page must include LanguageToggle");
    assert.ok(meContent.includes("handleToggleCoach"), "Me page must include coach toggle");

    const consentContent = fs.readFileSync(path.resolve("src/app/consent/page.tsx"), "utf-8");
    assert.ok(consentContent.includes("handleAccept"), "Consent page must include accept handler");
    assert.ok(consentContent.includes("handleDecline"), "Consent page must include decline handler");
  });
});
