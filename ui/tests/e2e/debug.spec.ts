import { test, expect } from '@playwright/test';

test('Debug page content', async ({ page }) => {
  // 收集所有控制台消息
  const consoleMessages: any[] = [];
  page.on('console', msg => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
    });
  });

  // 监听网络请求
  const failedRequests: string[] = [];
  page.on('requestfailed', request => {
    failedRequests.push(request.url());
  });

  await page.goto('/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  console.log('\n=== Console Messages ===');
  consoleMessages.forEach(msg => {
    console.log(`[${msg.type}] ${msg.text}`);
  });

  console.log('\n=== Failed Requests ===');
  failedRequests.forEach(url => {
    console.log(`FAILED: ${url}`);
  });

  console.log('\n=== Page Content ===');
  const bodyText = await page.evaluate(() => document.body.innerText);
  console.log('Body text length:', bodyText.length);
  console.log('Body text preview:', bodyText.substring(0, 200));

  const rootHTML = await page.locator('#root').innerHTML();
  console.log('Root HTML length:', rootHTML.length);
  console.log('Root HTML:', rootHTML.substring(0, 500));

  const hasLayout = await page.locator('.ant-layout').count();
  console.log('Ant Design layouts found:', hasLayout);

  const hasMenu = await page.locator('.ant-menu').count();
  console.log('Menus found:', hasMenu);

  await page.screenshot({
    path: 'screenshots/debug-full-page.png',
    fullPage: true
  });
});
