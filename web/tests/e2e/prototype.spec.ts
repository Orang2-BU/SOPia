import { expect, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const evidenceDir = path.resolve(process.cwd(), "../docs/evidence");

test.beforeAll(async () => {
  await mkdir(evidenceDir, { recursive: true });
});

test("Pages chat completes an approval workflow and exposes audit trail", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "Halo, Andi" })).toBeVisible();
  await expect(page.getByText("API terhubung")).toBeVisible();

  await page.locator("#message").fill(
    "Ajukan lembur 3 jam untuk 3 orang pada tanggal 20-22 Oktober 2026 karena tutup buku bulanan",
  );
  await page.getByRole("button", { name: "Kirim pesan" }).click();
  await expect(page.locator(".citation").first()).toContainText("SOP-LEMBUR-04");
  await expect(page.locator(".message-row.assistant").last()).toContainText("Menurut SOP-LEMBUR-04");
  await expect(page.locator(".message-row.assistant .bubble").last()).not.toContainText("##");
  await expect(page.getByRole("button", { name: /Jalankan rencana/ })).toBeEnabled();
  await page.screenshot({ path: path.join(evidenceDir, "chat-citation-plan.png"), fullPage: true });

  await page.getByRole("button", { name: /Jalankan rencana/ }).click();
  await expect(page.getByText("Perlu persetujuan")).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "approval-pending.png"), fullPage: true });
  await page.getByRole("button", { name: "Setujui" }).click();
  await expect(page.getByText("Selesai").first()).toBeVisible();

  await page.getByRole("button", { name: "Jejak audit" }).click();
  await expect(page.getByText("Riwayat proses")).toBeVisible();
  await expect(page.getByText(/approval_decided/)).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "audit-trail.png"), fullPage: true });
});

test("Pages uploads a new SOP and answers from its passage", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: "Dokumen SOP" }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: "sop-training-e2e.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      "## SOP-TRAINING-E2E-07 — Kode latihan\n\nKode latihan VIOLET-ORBIT-739 harus disimpan di brankas tim.",
    ),
  });
  await expect(page.getByText("SOP-TRAINING-E2E-07").first()).toBeVisible();
  await expect(page.getByText("Terindeks").last()).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "sop-uploaded.png"), fullPage: true });

  await page.getByRole("button", { name: "Asisten SOP" }).click();
  await page.locator("#message").fill("Di mana kode latihan VIOLET-ORBIT-739 harus disimpan?");
  await page.getByRole("button", { name: "Kirim pesan" }).click();
  await expect(page.locator(".citation").filter({ hasText: "SOP-TRAINING-E2E-07" })).toBeVisible();
  await expect(page.getByText(/brankas tim/).first()).toBeVisible();
});

test("mobile layout keeps SOP navigation available without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");
  await expect(page.getByRole("navigation", { name: "Navigasi utama seluler" })).toBeVisible();
  await page.getByRole("button", { name: "Dokumen SOP" }).last().click();
  await expect(page.getByRole("heading", { name: "Dokumen SOP" })).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
  await page.screenshot({ path: path.join(evidenceDir, "mobile-sop-navigation.png"), fullPage: true });
});
