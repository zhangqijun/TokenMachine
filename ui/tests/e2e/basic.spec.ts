import { test, expect } from '@playwright/test';

test.describe('Application Basic Tests', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 检查标题
    await expect(page).toHaveTitle(/web/);

    // 截图保存
    await page.screenshot({ path: 'screenshots/homepage.png' });
  });

  test('check for console errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 等待一下确保所有资源加载
    await page.waitForTimeout(3000);

    if (errors.length > 0) {
      console.log('=== Console Errors Found ===');
      errors.forEach(err => console.log(err));
    }

    expect(errors.length).toBe(0);
  });

  test('check root element exists', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const root = page.locator('#root');
    await expect(root).toBeVisible();

    // 检查是否有内容渲染
    const rootContent = await root.innerHTML();
    console.log('Root content length:', rootContent.length);

    if (rootContent.length === 0) {
      console.log('Root element is empty!');
      await page.screenshot({ path: 'screenshots/empty-root.png' });
    }
  });
});
