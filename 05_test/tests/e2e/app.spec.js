const { test, expect } = require('@playwright/test');

test.describe('E2E Test: 猜數字流程', () => {
  test.beforeEach(async ({ page }) => {
    // 固定 Math.random，讓答案固定為 43，測試結果可重現
    await page.addInitScript(() => {
      Math.random = () => 0.42;
    });
    await page.goto('/');
  });

  test('使用者可依照提示逐步猜中答案', async ({ page }) => {
    await expect(page.locator('#title')).toHaveText('猜數字遊戲');

    await page.fill('#guess-input', '50');
    await page.click('#guess-btn');
    await expect(page.locator('#message')).toHaveText('太大了！數字在 1 ~ 50 之間');
    await expect(page.locator('#range-display')).toHaveText('1 ~ 50');

    await page.fill('#guess-input', '10');
    await page.click('#guess-btn');
    await expect(page.locator('#message')).toHaveText('太小了！數字在 10 ~ 50 之間');
    await expect(page.locator('#range-display')).toHaveText('10 ~ 50');

    await page.fill('#guess-input', '43');
    await page.click('#guess-btn');
    await expect(page.locator('#message')).toHaveText('恭喜猜中！答案就是 43');
    await expect(page.locator('#attempts')).toHaveText('已猜次數: 3');
  });

  test('新遊戲會重置次數與提示', async ({ page }) => {
    await page.fill('#guess-input', '43');
    await page.click('#guess-btn');
    await expect(page.locator('#message')).toHaveText('恭喜猜中！答案就是 43');

    await page.click('#new-game-btn');
    await expect(page.locator('#message')).toHaveText('請輸入你的猜測');
    await expect(page.locator('#attempts')).toHaveText('已猜次數: 0');
    await expect(page.locator('#range-display')).toHaveText('1 ~ 100');
  });

  test('輸入範圍外的數字會顯示錯誤提示', async ({ page }) => {
    await page.fill('#guess-input', '150');
    await page.click('#guess-btn');
    await expect(page.locator('#message')).toHaveText('請輸入 1 到 100 的整數');
  });
});
