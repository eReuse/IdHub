// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

const TEST_DEVICEHUB_SITE = process.env.TEST_DEVICEHUB_SITE || 'http://127.0.0.1:8000'
const TEST_DEVICEHUB_USER = process.env.TEST_DEVICEHUB_USER || 'user@example.org'
const TEST_DEVICEHUB_PASSWD = process.env.TEST_DEVICEHUB_PASSWD || '1234'

async function login(page, date, time) {
    await page.goto(TEST_DEVICEHUB_SITE);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(TEST_DEVICEHUB_USER);
    await page.getByPlaceholder('Password').fill(TEST_DEVICEHUB_PASSWD);
    await page.getByPlaceholder('Password').press('Enter');
}

test('Connect to DLT', async ({ page }) => {
    await login(page);

    // DEBUG
    //await page.pause();
});
