// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

const TEST_DEVICEHUB_SITE = process.env.TEST_SITE || 'http://127.0.0.1:9001'
const TEST_DEVICEHUB_USER = process.env.TEST_USER || 'user@example.org'
const TEST_DEVICEHUB_PASSWD = process.env.TEST_PASSWD || '1234'

const TEST_SEARCH_SITE = process.env.TEST_SEARCH_SITE || 'http://127.0.0.1'

async function devicehub_credentials(page, date, time) {
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(TEST_DEVICEHUB_USER);
    await page.getByPlaceholder('Password').fill(TEST_DEVICEHUB_PASSWD);
    await page.getByPlaceholder('Password').press('Enter');
}

async function devicehub_login(page, date, time) {
    await page.goto(TEST_DEVICEHUB_SITE);
    await devicehub_credentials(page);
}

test('dpp search and verify', async ({ page }) => {
    await page.goto(TEST_SEARCH_SITE);
    await page.getByPlaceholder('Enter your search query').click();
    await page.getByPlaceholder('Enter your search query').fill('leonvo');
    await page.getByRole('button', { name: 'Search' }).click();

    await page.getByRole('link', { name: 'LENOVO 3227A2G' }).first().click();
    await page.getByRole('button', { name: '7325be8b6bab24d019015a9caf16cdd539126ecd49976b73e4a20ff58fab7e57' }).click();
    await page.getByRole('tab', { name: 'Proofs' }).click();
    await page.getByRole('button', { name: 'Verify', exact: true }).click();
    await page.getByRole('button', { name: 'Trust chain' }).click();
    await page.getByRole('button', { name: 'Verify' }).click();
    await page.getByRole('tab', { name: 'Info' }).click();
    await page.getByRole('link', { name: 'Link to inventory DPP' }).click();
    await page.getByRole('button', { name: 'Validate' }).click();
    await page.getByRole('link', { name: 'User of system' }).click();
    await devicehub_credentials(page);
    // DEBUG
    //await page.pause();
});
