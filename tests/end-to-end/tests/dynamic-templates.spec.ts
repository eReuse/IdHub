// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

// TEMP
//const TEST_SITE = process.env.TEST_SITE || 'http://127.0.0.1:9001'
const TEST_SITE = process.env.TEST_SITE || 'https://lab7.demo.ereuse.org'

const TEST_ADMIN_USER = process.env.TEST_USER || 'admin@example.org'
const TEST_ADMIN_PASSWD = process.env.TEST_PASSWD || 'admin'

const TEST_USER = process.env.TEST_USER || 'user1@example.org'
const TEST_USER_PASSWD = process.env.TEST_PASSWD || '1234'

// optional flow (only first time per idhub service start)
async function set_org_key(page) {
    //const encryption_key_page = page.getByText('Encryption Key')
    const encryption_key_page_admin = await page.getByRole('heading', { name: 'Encryption Key', exact: true })
    if (await encryption_key_page_admin.isVisible()) {
        await page.getByPlaceholder('Key for encrypt the secrets').click();
        await page.getByPlaceholder('Key for encrypt the secrets').fill('1234');
        await page.getByRole('button', { name: 'Save' }).click();
    }
}

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


async function login(page, user, password) {
    await page.goto(`${TEST_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(user);
    await page.getByPlaceholder('Password').fill(password);
    await page.getByPlaceholder('Password').press('Enter');
}

// https://stackoverflow.com/questions/73338339/playwright-framework-is-there-a-way-we-can-execute-dependent-tests-in-playwrig

test.describe.serial("dynamic template tour", ()=> {
    test('admin', async ({ page }) => {
        test.setTimeout(0)
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        // DEBUG
        await page.pause()

        await set_org_key(page);

        await accept_data_protection(page);

        // TODO fix popups
    });

    test('user', async ({ page }) => {
        test.setTimeout(0)
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        await accept_data_protection(page);
    });
});
