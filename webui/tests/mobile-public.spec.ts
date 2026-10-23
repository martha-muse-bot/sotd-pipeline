import { test, expect } from '@playwright/test';

// Mobile-viewport checks for the public analytics site. Runs against the same
// wiring as public-build.spec.ts (public build served on localhost:3000).
test.use({ viewport: { width: 375, height: 812 }, hasTouch: true });

test('hamburger nav opens and closes the menu', async ({ page }) => {
  await page.goto('/');
  const toggle = page.getByRole('button', { name: 'Toggle navigation menu' });
  await expect(toggle).toBeVisible();
  await expect(page.getByTestId('mobile-nav')).toBeHidden();

  await toggle.tap();
  const panel = page.getByTestId('mobile-nav');
  await expect(panel).toBeVisible();
  await expect(panel.getByRole('link')).toHaveCount(4); // Home + 3 pages

  // Navigating from the menu closes it
  await panel.getByRole('link', { name: 'Product Usage' }).tap();
  await expect(page).toHaveURL(/\/product-usage/);
  await expect(page.getByTestId('mobile-nav')).toBeHidden();
});

test('desktop nav is used at larger viewports', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Toggle navigation menu' })).toBeHidden();
  await expect(page.getByRole('navigation').getByRole('link')).toHaveCount(4);
  await ctx.close();
});
