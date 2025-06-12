// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

const TEST_IDHUB_SITE = process.env.TEST_IDHUB_SITE || 'http://127.0.0.1:9001'
const TEST_IDHUB_USER = process.env.TEST_IDHUB_USER || 'admin@example.org'
const TEST_IDHUB_PASSWD = process.env.TEST_IDHUB_PASSWD || 'admin'

async function login(page, date, time) {
    await page.goto(`${TEST_IDHUB_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(TEST_IDHUB_USER);
    await page.getByPlaceholder('Password').fill(TEST_IDHUB_PASSWD);
    await page.getByPlaceholder('Password').press('Enter');
}

test('Create WIP Credential', async ({ page }) => {
    await login(page);
    await page.goto(`${TEST_IDHUB_SITE}/admin/dashboard/`);
    await page.getByRole('link', { name: ' Data' }).click();
    await page.getByRole('link', { name: 'Import data ' }).click();
    await page.getByLabel('Did').selectOption({ label: 'dpp' });
    await page.getByLabel('Schema').selectOption({ label: 'TI member part of TAO' });
    const cred_path = path.resolve(__dirname, '../examples/OrganizationMembershipDlt-credential.xlsx');
    await page.getByLabel('File to import').setInputFiles(cred_path);
    await page.getByRole('button', { name: 'Save' }).click();
});
