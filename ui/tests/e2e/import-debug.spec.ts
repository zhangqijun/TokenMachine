import { test, expect } from '@playwright/test';

test('Debug imports', async ({ page }) => {
  const errors: string[] = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  page.on('pageerror', error => {
    console.log('PAGE ERROR:', error.toString());
    errors.push(error.toString());
  });

  page.on('load', () => {
    console.log('Page loaded');
  });

  page.on('domcontentloaded', () => {
    console.log('DOMContentLoaded fired');
  });

  await page.goto('/', { waitUntil: 'domcontentloaded' });

  // 等待一会儿
  await page.waitForTimeout(5000);

  console.log('\n=== Final Check ===');
  const rootHTML = await page.locator('#root').innerHTML();
  console.log('Root HTML length:', rootHTML.length);

  if (errors.length > 0) {
    console.log('\n=== Errors Found ===');
    errors.forEach(err => console.log(err));
  }

  await page.screenshot({
    path: 'screenshots/import-debug.png',
    fullPage: true
  });
});
