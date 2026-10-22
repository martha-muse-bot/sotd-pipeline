import { test, expect } from '@playwright/test';

// Runs against the public build served by `manage-servers.sh` (public mode)
// or vite preview for dist-public. Verifies the curated nav only.
// NOTE: the manage-servers.sh --public mode was deferred to the controller
// (servers already run externally in the containerization rollout); this spec
// is written for that wiring and is not yet invoked by the script.
test('public home lists exactly the three analytics pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('SOTD Analytics')).toBeVisible();
  const links = page.getByRole('navigation').getByRole('link');
  await expect(links).toHaveCount(4); // Home + 3 pages
});

test('deep link to product usage renders the SPA', async ({ page }) => {
  await page.goto('/product-usage');
  await expect(page.locator('main')).toBeVisible();
});
