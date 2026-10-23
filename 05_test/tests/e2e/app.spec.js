const { test, expect } = require('@playwright/test');

test.describe('E2E Test: 購物流程', () => {
  test('使用者點擊加入商品並結帳後，畫面上會顯示正確金額', async ({ page }) => {
    await page.goto('http://localhost:3000');

    await expect(page.locator('#title')).toHaveText('簡易購物車');
    await page.click('#add-item-btn');
    await page.click('#checkout-btn');

    await expect(page.locator('#total-price')).toHaveText('總計: $100');
  });
});