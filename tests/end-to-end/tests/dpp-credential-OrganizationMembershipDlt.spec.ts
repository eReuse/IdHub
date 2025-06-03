// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

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

test('Create WIP Credential', async ({ page }) => {
    await login(page);

    await page.goto('http://127.0.0.1:9001/admin/dashboard/');
    await page.getByRole('link', { name: ' Data' }).click();
    await page.getByRole('link', { name: 'Import data ' }).click();
    await page.getByLabel('Did').selectOption({ label: 'dpp' });
    await page.getByLabel('Schema').selectOption('6');
    const cred_path = path.resolve(__dirname, '../examples/OrganizationMembershipDlt-credential.xlsx');
    await page.getByLabel('File to import').setInputFiles(cred_path);
    await page.getByRole('button', { name: 'Save' }).click();
    // DEBUG
    await page.pause();
});
