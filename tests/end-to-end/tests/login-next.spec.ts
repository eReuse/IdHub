import { test, expect } from '@playwright/test';
import { login, accept_data_protection } from './helpers/flows';
import { TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD } from './helpers/config';

test.describe('Authentication Redirects', () => {

    test('admin wants url, but login is required', async ({ page }) => {
        await page.goto(`${TEST_SITE}/admin/wallet/identities/`);
        await page.getByPlaceholder('Email address').fill(TEST_ADMIN_USER);
        await page.getByPlaceholder('Password').fill(TEST_ADMIN_PASSWD);
        await page.getByPlaceholder('Password').press('Enter');

        await accept_data_protection(page);
        await expect(page.locator('h1')).toContainText('Credential management');
    });

    test('when admin user goes to login, redirect to admin dashboard', async ({ page }) => {
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
        await accept_data_protection(page);
        await expect(page.locator('h1')).toContainText('Dashboard');
        await expect(page).toHaveURL(/admin\/dashboard/);
    });

    test('when user goes to login, redirect to dashboard of user', async ({ page }) => {
        await login(page, TEST_USER, TEST_USER_PASSWD);
        await accept_data_protection(page);
        await expect(page).toHaveURL(/user\/dashboard/);
    });

    test('user tries admin url, should redirect to dashboard of user', async ({ page }) => {
        await page.goto(`${TEST_SITE}/admin/wallet/identities/`);
        await page.getByPlaceholder('Email address').fill(TEST_USER);
        await page.getByPlaceholder('Password').fill(TEST_USER_PASSWD);
        await page.getByPlaceholder('Password').press('Enter');

        await accept_data_protection(page);
        await expect(page).toHaveURL(/user\/dashboard/);
        // DEBUG
        //await page.pause();

    });
});
