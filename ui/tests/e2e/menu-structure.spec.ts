import { test, expect } from '@playwright/test';

test.describe('Menu Structure', () => {
  test('验证侧边栏菜单结构', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 获取所有菜单项
    const menuItems = await page.locator('.ant-menu-item').allTextContents();
    console.log('菜单项:', menuItems);

    // 验证菜单项
    const expectedMenus = ['仪表盘', '节点与后端', '模型与实例', '测试场', '监控面板', '网关管理', '系统设置'];
    for (const menu of expectedMenus) {
      const exists = menuItems.some(item => item.includes(menu));
      expect(exists).toBe(true);
    }

    // 验证没有不应该存在的菜单
    const notExpectedMenus = ['部署管理', '资源管理'];
    for (const menu of notExpectedMenus) {
      const exists = menuItems.some(item => item.includes(menu));
      expect(exists).toBe(false);
    }

    console.log('✓ 菜单结构验证通过');
  });

  test('验证顶部导航栏元素', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 验证搜索框
    const searchInput = page.locator('.ant-input-search');
    await expect(searchInput).toBeVisible();
    console.log('✓ 搜索框存在');

    // 验证帮助文档图标
    const helpIcon = page.locator('.anticon-question-circle');
    await expect(helpIcon).toBeVisible();
    console.log('✓ 帮助文档图标存在');

    // 验证通知图标
    const bellIcon = page.locator('.anticon-bell');
    await expect(bellIcon).toBeVisible();
    console.log('✓ 通知图标存在');

    // 验证用户头像
    const avatar = page.locator('.ant-avatar');
    await expect(avatar).toBeVisible();
    console.log('✓ 用户头像存在');

    // 验证 Header 是否固定
    const header = page.locator('.ant-layout-header');
    const position = await header.evaluate(el => getComputedStyle(el).position);
    expect(position).toBe('sticky');
    console.log('✓ Header 固定在顶部');
  });
});
