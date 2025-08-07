// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

const TEST_SITE = process.env.TEST_SITE || 'http://localhost'

const TEST_ADMIN_USER = process.env.TEST_ADMIN_USER || 'admin@example.org'
const TEST_ADMIN_PASSWD = process.env.TEST_PASSWD || 'admin'

const TEST_USER = process.env.TEST_USER || 'user1@example.org'
const TEST_USER_PASSWD = process.env.TEST_PASSWD || '1234'

// optional flow (only first time per idhub service start)
async function set_org_key(page) {
    //const encryption_key_page = page.getByText('Encryption Key')
    const encryption_key_page_admin = await page.getByRole('heading', { name: 'Encryption Key', exact: true })
    if (await encryption_key_page_admin.isVisible()) {
        await page.getByPlaceholder('Key for encrypt the secrets').click();
        await page.getByPlaceholder('Key for encrypt the secrets').fill('DEMO');
        await page.getByRole('button', { name: 'Save' }).click();
    }
}

async function login(page, user, password) {
    await page.goto(`${TEST_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(user);
    await page.getByPlaceholder('Password').fill(password);
    await page.getByPlaceholder('Password').press('Enter');
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
                await page.waitForTimeout(1000);
                await page.getByRole('link', { name: 'Confirm' }).click();
        }
}

test('credential without html template', async ({ page }) => {
    test.setTimeout(0)
    await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
    await set_org_key(page);
    await accept_data_protection(page);

    // TODO problem?
    //await page.waitForTimeout(2000);
    //await page.pause();
    //await page.wait_for_load_state()
    await page.getByRole('link', { name: ' Templates' }).click();
    await page.getByRole('link', { name: 'Schemas' }).click();
    await page.getByRole('link', { name: 'Upload template ' }).click();
    await page.getByRole('button', { name: 'Enable Schema from URL' }).click();
    await page.getByRole('textbox', { name: 'Schema url reference' }).fill('https://idhub.pangea.org/vc_schemas/course-credential.json');
    await page.getByRole('textbox', { name: 'Context url reference' }).click();
    await page.getByRole('textbox', { name: 'Context url reference' }).fill('https://idhub.pangea.org/context/course-credential.jsonld');
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('link', { name: ' Data' }).click();
    await page.getByRole('link', { name: 'Import data ' }).click();
    await page.getByLabel('Schema').selectOption('1');
    const filexlsx_path = path.resolve(__dirname, '../../../examples/excel_examples/course-credential.xlsx');
    await page.getByLabel('File to import').setInputFiles(filexlsx_path);
    await page.getByRole('button', { name: 'Save' }).click();
    // logout
    await page.getByRole('link', { name: '' }).click();
    await login(page, TEST_USER, TEST_USER_PASSWD);
    await accept_data_protection(page);
    await page.getByRole('link', { name: 'Request a credential' }).click();
    await page.getByRole('button', { name: 'Request' }).click();
    await page.getByRole('link', { name: '' }).click();
    const page1Promise = page.waitForEvent('popup');
    await page.getByRole('link', { name: 'View as HTML' }).click();
    const page1 = await page1Promise;
});

test('credential with html template', async ({ page }) => {
    test.setTimeout(0)
    await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

    //await page.wait_for_load_state("load")
    await page.getByRole('link', { name: ' Templates' }).click();
    await page.getByRole('link', { name: 'Templates PDF' }).click();
    await page.getByRole('link', { name: 'Upload new template ' }).click();
    await page.goto(`${TEST_SITE}/admin/templates_pdf/new/`);

    await page.getByRole('textbox', { name: 'Name' }).click();
    await page.getByRole('textbox', { name: 'Name' }).fill('course');
    const cred_path = path.resolve(__dirname, '../../../examples/course-credential_es.html');
    await page.getByLabel('Data').setInputFiles(cred_path);
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('link', { name: ' Data' }).click();
    await page.getByRole('link', { name: 'Import data ' }).click();
    await page.getByLabel('Select one template for').selectOption('1');
    await page.getByLabel('Schema').selectOption('1');
    const filexlsx_path = path.resolve(__dirname, '../../../examples/excel_examples/course-credential.xlsx');
    await page.getByLabel('File to import').setInputFiles(filexlsx_path);
    await page.getByRole('button', { name: 'Save' }).click();

    // logout
    await page.getByRole('link', { name: '' }).click();

    await login(page, TEST_USER, TEST_USER_PASSWD);

    await accept_data_protection(page);

    await page.getByRole('link', { name: 'Request a credential' }).click();
    await page.getByRole('button', { name: 'Request' }).click();
    await page.getByRole('link', { name: '' }).first().click();
    const page1Promise = page.waitForEvent('popup');
    await page.getByRole('link', { name: 'View as HTML' }).click();
    const page1 = await page1Promise;
    //await page.pause();
});
