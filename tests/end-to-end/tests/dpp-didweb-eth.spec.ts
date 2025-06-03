// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

const TEST_DEVICEHUB_SITE = process.env.TEST_DEVICEHUB_SITE || 'http://127.0.0.1:9001'
const TEST_DEVICEHUB_USER = process.env.TEST_DEVICEHUB_USER || 'admin@example.org'
const TEST_DEVICEHUB_PASSWD = process.env.TEST_DEVICEHUB_PASSWD || 'admin'

async function login(page, date, time) {
    await page.goto(TEST_DEVICEHUB_SITE);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(TEST_DEVICEHUB_USER);
    await page.getByPlaceholder('Password').fill(TEST_DEVICEHUB_PASSWD);
    await page.getByPlaceholder('Password').press('Enter');
}

test('Create did Web+Ether', async ({ page }) => {
    await login(page);

    await page.getByRole('link', { name: ' Credentials' }).click();
    await page.getByRole('link', { name: 'Organization\'s wallet' }).click();
    await page.getByRole('link', { name: 'Manage Identities (DIDs)' }).click();
    await page.getByRole('link', { name: 'Add identity ' }).click();
    await page.getByPlaceholder('Label').click();
    await page.getByPlaceholder('Label').fill('dpp');
    await page.getByLabel('Type').selectOption('3');
    await page.getByRole('button', { name: 'Save' }).click();

    // DEBUG
    await page.pause();
});
