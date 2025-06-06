// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

const TEST_SITE = process.env.TEST_SITE || 'http://127.0.0.1:9001'

const TEST_ADMIN_USER = process.env.TEST_USER || 'admin@example.org'
const TEST_ADMIN_PASSWD = process.env.TEST_PASSWD || 'admin'

const TEST_USER = process.env.TEST_USER || 'user1@example.org'
const TEST_USER_PASSWD = process.env.TEST_PASSWD || '1234'

// optional page (decrypt)
// src https://playwright.dev/docs/locators#matching-one-of-the-two-alternative-locators
async function accept_data_protection(page) {
        // TODO cannot be, because of this inconsistency: Data Protection (user) vs Data protection (admin)
        //const data_protection = await page.getByRole('heading', { name: 'Data protection', exact: true })
        const data_protection = await page.getByRole('heading', { name: 'Data protection' })
        if (await data_protection.isVisible()) {
                await page.locator('#id_accept_privacy').check();
                await page.locator('#id_accept_legal').check();
                await page.locator('#id_accept_cookies').check();
                await page.getByRole('link', { name: 'Confirm' }).click();
        }
}

async function put_login_credentials(page, email, passwd) {
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(email);
    await page.getByPlaceholder('Password').fill(passwd);
    await page.getByPlaceholder('Password').press('Enter');
}

test('admin wants url, but login is required', async ({ page }) => {
    test.setTimeout(0)
    await page.goto(`${TEST_SITE}/admin/wallet/identities/`);
    await put_login_credentials(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
    await accept_data_protection(page);
    await expect(page.locator('h1')).toContainText('Credential management');
});


test('when admin user goes to login, redirect to admin dashboard', async ({ page }) => {
    test.setTimeout(0)
    await page.goto(`${TEST_SITE}/login/`);
    await put_login_credentials(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
    await accept_data_protection(page);
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page).toHaveURL(new RegExp('admin/dashboard'));
});

test('when user goes to login, redirect to user dashboard', async ({ page }) => {
    test.setTimeout(0)
    await page.goto(`${TEST_SITE}/login/`);
    await put_login_credentials(page, TEST_USER, TEST_USER_PASSWD);
    await accept_data_protection(page);
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page).toHaveURL(new RegExp('user/dashboard'));
});

test('user tries url from admin, should go to dashboard', async ({ page }) => {
    test.setTimeout(0)
    await page.goto(`${TEST_SITE}/admin/wallet/identities/`);
    await put_login_credentials(page, TEST_USER, TEST_USER_PASSWD);
    await accept_data_protection(page);
    await expect(page.locator('h1')).toContainText('Dashboard');

    // DEBUG
    //await page.pause();
});
