import { test, expect } from '@playwright/test';

test.describe('Safari Basic Functionality', () => {
  test('should load the app and display navigation', async ({ page }) => {
    // Mock API calls to avoid real network requests
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      });
    });

    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Basic app structure checks
    await expect(page).toHaveTitle(/SOTD Pipeline Analyzer/);
    await expect(page.locator('#root')).toBeVisible();
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();

    // Check navigation groups exist — the header uses grouped dropdowns
    // (three buttons: Analyzers, Validators, Tools) since 1448785ce, not
    // a flat list of links.
    const navButtons = page.locator('nav button');
    await expect(navButtons).toHaveCount(3);
  });

  test('should handle navigation between pages', async ({ page }) => {
    // Mock API calls
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      });
    });

    await page.goto('/');

    // Wait for page load
    await page.waitForLoadState('networkidle');

    // Open the Analyzers dropdown and navigate via one of its links
    await page.getByRole('button', { name: /Analyzers/ }).click();
    const productUsageLink = page.getByRole('link', { name: /Product Usage/ });

    await expect(productUsageLink).toBeVisible();
    await productUsageLink.click();

    // Verify we navigated (URL changed to the product usage page)
    await expect(page).toHaveURL(/product-usage/);
  });

  test('should handle form interactions', async ({ page }) => {
    // Mock API calls
    await page.route('**/api/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok' }),
      });
    });

    await page.goto('/');

    // Wait for page load
    await page.waitForLoadState('networkidle');

    // Test basic form interactions if they exist
    const inputs = page.locator('input, select, textarea');
    const buttons = page.locator('button');

    // Verify forms are interactive
    if ((await inputs.count()) > 0) {
      const firstInput = inputs.first();
      await firstInput.focus();
      await expect(firstInput).toBeFocused();
    }

    if ((await buttons.count()) > 0) {
      const firstButton = buttons.first();
      await expect(firstButton).toBeVisible();
    }
  });
});
