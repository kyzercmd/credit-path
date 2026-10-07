import { test, describe } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";

describe("Task 10: Admin Panel Verification (U1-U6)", () => {
  const adminFiles = [
    "src/app/admin/page.tsx",
    "src/components/admin/FunnelTable.tsx",
    "src/components/admin/ForecastQuality.tsx",
    "src/components/admin/RuleSettings.tsx",
    "src/components/admin/FairnessPanel.tsx",
    "src/components/admin/KillSwitch.tsx",
    "src/components/admin/AuditLog.tsx",
  ];

  test("All 7 admin files exist on disk with meaningful content", () => {
    for (const filePath of adminFiles) {
      const fullPath = path.resolve(filePath);
      assert.ok(fs.existsSync(fullPath), `File missing: ${filePath}`);
      const content = fs.readFileSync(fullPath, "utf-8");
      assert.ok(content.length > 300, `File content too short: ${filePath}`);
    }
  });

  test("FunnelTable (U1) implements ready/not-yet counts and missing checks", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/FunnelTable.tsx"), "utf-8");
    assert.ok(content.includes("total_customers"), "Must display total customers");
    assert.ok(content.includes("ready_count"), "Must display ready count");
    assert.ok(content.includes("not_yet_count"), "Must display not yet count");
    assert.ok(content.includes("missing_checks"), "Must process missing checks");
    assert.ok(content.includes("Borrowing history"), "Must map to Borrowing history check");
    assert.ok(content.includes("Regular income"), "Must map to Regular income check");
    assert.ok(content.includes("Repayment cushion & bills"), "Must map to Repayment cushion & bills check");
  });

  test("ForecastQuality (U2) implements MAE/WAPE vs naive baseline and persona cohorts", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/ForecastQuality.tsx"), "utf-8");
    assert.ok(content.includes("overall_mae"), "Must display overall MAE");
    assert.ok(content.includes("overall_wape"), "Must display overall WAPE");
    assert.ok(content.includes("naive_mae"), "Must display naive baseline MAE");
    assert.ok(content.includes("naive_wape"), "Must display naive baseline WAPE");
    assert.ok(content.includes("wage_worker"), "Must contain wage_worker persona");
    assert.ok(content.includes("seasonal_farmer"), "Must contain seasonal_farmer persona");
    assert.ok(content.includes("informal_merchant"), "Must contain informal_merchant persona");
    assert.ok(content.includes("woman_led_household"), "Must contain woman_led_household persona");
    assert.ok(content.includes("salaried_user"), "Must contain salaried_user persona");
  });

  test("RuleSettings (U3) includes all 8 editable thresholds, version timestamp, and putAdminConfig", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/RuleSettings.tsx"), "utf-8");
    const requiredInputs = [
      "min_history_months",
      "min_bill_payment_rate",
      "min_income_months",
      "min_cushion_ratio",
      "max_dti_ratio",
      "stress_income_drop_pct",
      "annual_interest_rate_pct",
      "max_loan_cap",
    ];

    for (const inputKey of requiredInputs) {
      assert.ok(content.includes(inputKey), `Must contain threshold input: ${inputKey}`);
    }

    assert.ok(content.includes("putAdminConfig"), "Must call putAdminConfig API");
    assert.ok(content.includes("version"), "Must display configuration version");
    assert.ok(content.includes("timestamp"), "Must display version timestamp");
  });

  test("FairnessPanel (U4) includes demographic tables (gender, region, age), N/A handling, and mitigation", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/FairnessPanel.tsx"), "utf-8");
    assert.ok(content.includes("by_gender"), "Must render gender breakdown");
    assert.ok(content.includes("by_region"), "Must render region breakdown");
    assert.ok(content.includes("by_age_band"), "Must render age band breakdown");
    assert.ok(content.includes("ready_rate"), "Must render ready rate");
    assert.ok(content.includes("forecast_error"), "Must render forecast error");
    assert.ok(content.includes("false_not_yet_rate"), "Must render false not yet rate");
    assert.ok(content.includes('"N/A"'), "Must format empty or null values as N/A");
    assert.ok(content.includes("mitigation"), "Must display policy mitigation");
    assert.ok(content.includes("before"), "Must show mitigation before state");
    assert.ok(content.includes("after"), "Must show mitigation after state");
  });

  test("KillSwitch (U5) implements safe-range and loan-check toggles with warning styling and API call", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/KillSwitch.tsx"), "utf-8");
    assert.ok(content.includes("kill_safe_range"), "Must control kill_safe_range");
    assert.ok(content.includes("kill_loan_check"), "Must control kill_loan_check");
    assert.ok(content.includes("postAdminKillSwitch"), "Must invoke postAdminKillSwitch API");
    assert.ok(content.includes("AlertOctagon") || content.includes("alert"), "Must include warning alerts");
  });

  test("AuditLog (U6) renders audit event table with event_type, details, and timestamp", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/AuditLog.tsx"), "utf-8");
    assert.ok(content.includes("event_type"), "Must display event_type");
    assert.ok(content.includes("details"), "Must display details");
    assert.ok(content.includes("timestamp"), "Must display timestamp");
  });
  test("Admin page organizes all 6 sections, navigation, skeletons, and error handling", () => {
    const content = fs.readFileSync(path.resolve("src/app/admin/page.tsx"), "utf-8");
    assert.ok(content.includes("FunnelTable"), "Must include FunnelTable");
    assert.ok(content.includes("ForecastQuality"), "Must include ForecastQuality");
    assert.ok(content.includes("RuleSettings"), "Must include RuleSettings");
    assert.ok(content.includes("FairnessPanel"), "Must include FairnessPanel");
    assert.ok(content.includes("KillSwitch"), "Must include KillSwitch");
    assert.ok(content.includes("AuditLog"), "Must include AuditLog");
    assert.ok(content.includes("/home"), "Must provide back navigation to /home");
    assert.ok(content.includes("ErrorState"), "Must include ErrorState handler");
    assert.ok(content.includes("data-admin-page"), "Must mark page with data-admin-page attribute");
  });

  test("ForecastQuality MAE Edge sign coloring, WAPE comparison, low-confidence badge, and tier tags", () => {
    const content = fs.readFileSync(path.resolve("src/components/admin/ForecastQuality.tsx"), "utf-8");
    // Sign logic for MAE Edge
    assert.ok(content.includes("edge > 0"), "Must test positive edge");
    assert.ok(content.includes("edge < 0"), "Must test negative edge");
    assert.ok(content.includes("text-emerald-700"), "Must style positive edge green");
    assert.ok(content.includes("text-red-600"), "Must style negative edge red");
    assert.ok(content.includes("text-[#6B6B76]"), "Must style zero edge gray");

    // Model WAPE comparison with Naive WAPE
    assert.ok(
      content.includes("Number(item.wape) > Number(item.naive_wape)") ||
        content.includes("isWapeWorse"),
      "Must compare Model WAPE vs Naive WAPE"
    );

    // Low confidence badge and tooltip
    assert.ok(content.includes("Low confidence"), "Must render Low confidence badge");
    assert.ok(
      content.includes("Forecast is not better than a simple baseline for this group yet."),
      "Must have exact low-confidence tooltip text"
    );

    // Persona tiers
    assert.ok(content.includes("Primary"), "Must render Primary tier tag");
    assert.ok(content.includes("Control"), "Must render Control tier tag");
    assert.ok(content.includes("Next phase"), "Must render Next phase tier tag");
  });
});

