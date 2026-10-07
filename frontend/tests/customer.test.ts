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

  test("Review fixes: progress bill payments, consent log, 30% safe range, and no surplus jargon", () => {
    // 1. Progress page displays bill payment on-time percentage
    const progressContent = fs.readFileSync(path.resolve("src/app/progress/page.tsx"), "utf-8");
    assert.ok(
      progressContent.includes("bill_payments_title") ||
        progressContent.includes("Bill payments on time"),
      "Progress page must display bill payment on-time percentage"
    );
    assert.ok(
      progressContent.includes("bill_on_time_pct"),
      "Progress page must use bill_on_time_pct metric"
    );

    // 2. Me page displays consent log
    const meContent = fs.readFileSync(path.resolve("src/app/me/page.tsx"), "utf-8");
    assert.ok(
      meContent.includes("consent_log") || meContent.includes("consentLog"),
      "Me page must display consent log"
    );

    // 3. Safe range copy states 30%
    const enJson = JSON.parse(fs.readFileSync(path.resolve("src/i18n/en.json"), "utf-8"));
    const bnJson = JSON.parse(fs.readFileSync(path.resolve("src/i18n/bn.json"), "utf-8"));
    assert.ok(
      enJson.safe_range.stressed_range.includes("30%"),
      "Safe range English copy must state 30%"
    );
    assert.ok(
      bnJson.safe_range.stressed_range.includes("৩০%"),
      "Safe range Bangla copy must state 30% (৩০%)"
    );

    // 4. Jargon 'surplus' is not present in customer screens
    const safeRangeContent = fs.readFileSync(path.resolve("src/app/safe-range/page.tsx"), "utf-8");
    assert.ok(
      !safeRangeContent.toLowerCase().includes("monthly surplus"),
      "SafeRange WhySheet must not use jargon 'monthly surplus'"
    );
    assert.ok(
      !safeRangeContent.includes("affordability_surplus_cap"),
      "SafeRange WhySheet code must not use 'affordability_surplus_cap'"
    );

    const loanContent = fs.readFileSync(path.resolve("src/app/loan-check/page.tsx"), "utf-8");
    assert.ok(
      !loanContent.toLowerCase().includes("of surplus"),
      "LoanCheck WhySheet must not use jargon 'of surplus'"
    );
    assert.ok(
      !loanContent.toLowerCase().includes("surplus = comfortable"),
      "LoanCheck WhySheet target must not use jargon 'surplus = Comfortable'"
    );

    // 5. Numeral formatting: customer screens consume from useLanguage()
    assert.ok(
      !safeRangeContent.includes('from "@/lib/format"'),
      "SafeRange must consume formatters from useLanguage()"
    );
    // 6. Low-confidence honest UI notice on Safe Range and Calendar
    assert.ok(
      safeRangeContent.includes("data.low_confidence"),
      "SafeRange must check data.low_confidence"
    );
    assert.ok(
      safeRangeContent.includes("low_confidence_notice"),
      "SafeRange must render low_confidence_notice"
    );

    const calContent = fs.readFileSync(path.resolve("src/app/calendar/page.tsx"), "utf-8");
    assert.ok(
      calContent.includes("data.low_confidence"),
      "Calendar must check data.low_confidence"
    );
    assert.ok(
      calContent.includes("low_confidence_notice"),
      "Calendar must render low_confidence_notice"
    );

    assert.strictEqual(
      enJson.safe_range.low_confidence_notice,
      "This estimate is less reliable for your income pattern."
    );
    assert.strictEqual(
      enJson.calendar.low_confidence_notice,
      "This estimate is less reliable for your income pattern."
    );
  });
});
