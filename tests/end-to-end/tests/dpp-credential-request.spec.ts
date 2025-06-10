// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

const TEST_IDHUB_SITE = process.env.TEST_IDHUB_SITE || 'http://127.0.0.1:9001'
const TEST_IDHUB_USER = process.env.TEST_IDHUB_USER || 'user1@example.org'
const TEST_IDHUB_PASSWD = process.env.TEST_IDHUB_PASSWD || '1234'

// optional page (decrypt)
// src https://playwright.dev/docs/locators#matching-one-of-the-two-alternative-locators
async function accept_data_protection(page) {
    const data_protection = await page.getByRole('heading', { name: 'Data protection' })
    if (await data_protection.isVisible()) {
        await page.locator('#id_accept_privacy').check();
        await page.locator('#id_accept_legal').check();
        await page.locator('#id_accept_cookies').check();
        await page.getByRole('link', { name: 'Confirm' }).click();
        }
}


async function login(page, date, time) {
    await page.goto(`${TEST_IDHUB_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(TEST_IDHUB_USER);
    await page.getByPlaceholder('Password').fill(TEST_IDHUB_PASSWD);
    await page.getByPlaceholder('Password').press('Enter');
}

test('Request WIP Credential', async ({ page }) => {
    await login(page);
    // DEBUG
    await page.pause();

    await accept_data_protection(page);
    await page.getByRole('link', { name: 'Request a credential' }).click();
    await page.getByPlaceholder('Label').click();
    await page.getByPlaceholder('Label').fill('dpp');
    await page.getByLabel('Type').selectOption({ label: 'Web+Ether' });
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('link', { name: 'Request a credential' }).click();
    await page.getByRole('button', { name: 'Request' }).click();
});
