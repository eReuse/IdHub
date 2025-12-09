// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

const TEST_SITE = process.env.TEST_SITE || 'http://127.0.0.1:9001'

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

async function initial_setup_html_eidas1(page) {
    await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

    await set_org_key(page);

    await accept_data_protection(page);

    // upload HTML template (for course-credential)
    ////
    await page.getByRole('link', { name: ' Templates' }).click();
    await page.getByRole('link', { name: 'Templates PDF' }).click();
    await page.getByRole('link', { name: 'Upload new template ' }).click();
    await page.getByPlaceholder('Name').click();
    await page.getByPlaceholder('Name').fill(`course-credential-template`);
    const cred_path = path.resolve(__dirname, '../../../examples/course-credential_es.html');
    await page.getByLabel('Data').setInputFiles(cred_path);
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('link', { name: ' Credentials' }).click();
    await page.getByRole('link', { name: 'View credentials' }).click();
    await page.getByRole('link', { name: 'Organization\'s wallet' }).click();

    // upload eIDAS1 key
    ////
    await page.getByRole('link', { name: 'Manage Identities' }).click();
    await page.getByRole('link', { name: 'Add identity eIDAS1 ' }).click();
    await page.getByPlaceholder('Label').click();
    await page.getByPlaceholder('Label').fill('mykey');
    await page.getByPlaceholder('Password of certificate').click();
    await page.getByPlaceholder('Password of certificate').fill('123456');
    const eidas1_path = path.resolve(__dirname, '../../../examples/signerDNIe004.pfx');
    await page.getByLabel('File import').setInputFiles(eidas1_path);
    await page.getByRole('button', { name: 'Upload' }).click();
    await page.getByRole('link', { name: 'Dashboard' }).click();
}

async function request_credential(page) {
    // login as user
    await login(page, TEST_USER, TEST_USER_PASSWD);
    await accept_data_protection(page);

    // request credential
    await page.getByRole('link', { name: 'Request a credential' }).click();
    await page.getByRole('button', { name: 'Request' }).click();
    await page.getByRole('link', { name: '' }).first().click();

    // click json and pdf file results
    const download1Promise = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download as JSON' }).click();
    const download1 = await download1Promise;

    // this button is optional
    const PDFbutton = page.getByRole('link', { name: 'Download as PDF' })
    if (await PDFbutton.isVisible()) {
        const download2Promise = page.waitForEvent('download');
        await PDFbutton.click();
        const download2 = await download2Promise;
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
test.describe.serial("dynamic template tour", () => {

    // // TODO this might be only for course credential
    // test.beforeAll(async ({ browser }) => {
    //     const ctx = await browser.newContext();
    //     const page = await ctx.newPage();
    // });

    // this must be first test because launches 'initial_setup_html_eidas1'
    test('[admin] enable credential by file with schema and context', async ({ page }) => {
        const credential = 'course-credential'

        // this is only for first test
        await initial_setup_html_eidas1(page);
        //await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        // upload schema by file
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Schemas' }).click();
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable from File' }).click();
        const schema_path = path.resolve(__dirname, `../../../schemas/${credential}.json`);
        await page.getByLabel('Schema to import').setInputFiles(schema_path);
        const context_path = path.resolve(__dirname, `../../../context/${credential}.jsonld`);
        await page.getByLabel('Context to import (optional)').setInputFiles(context_path);
        await page.getByRole('button', { name: 'Save' }).click();

        // import data
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        await page.getByLabel('Select one template for render to Pdf').selectOption('1');
        await page.getByLabel('Schema').selectOption('NGO Course Credential for participants');
        const data_path = path.resolve(__dirname, `../../../examples/excel_examples/${credential}.xlsx`);
        await page.getByLabel('File to import').setInputFiles(data_path);
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();
    });

    test('[user] request credential by file with schema and context', async ({ page }) => {
        await request_credential(page);
    });

    test('[admin] enable credential by file with schema and no context', async ({ page }) => {
        const credential = 'financial-vulnerability'

        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        // upload schema by file
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Schemas' }).click();
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable from File' }).click();
        const schema_path = path.resolve(__dirname, `../../../schemas/${credential}.json`);
        await page.getByLabel('Schema to import').setInputFiles(schema_path);
        await page.getByRole('button', { name: 'Save' }).click();

        // import data
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        //await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        // TODO template is only for course credential
        //await page.getByLabel('Select one template for render to Pdf').selectOption('1');
        await page.getByLabel('Schema').selectOption('Financial Vulnerability Credential');
        const data_path = path.resolve(__dirname, `../../../examples/excel_examples/${credential}.xlsx`);
        await page.getByLabel('File to import').setInputFiles(data_path);
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();
    });

    test('[user] request credential by file with schema and no context', async ({ page }) => {
        await request_credential(page);
    });

    test('[admin] enable credential by URL with schema and context', async ({ page }) => {
        const credential = 'membership-card'

        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        // TODO
        //await page.pause();

        // upload schema by URL
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Schemas' }).click();
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable from URL' }).click();

        await page.getByLabel('Schema url reference').fill(`https://idhub.pangea.org/vc_schemas/${credential}.json`);
        await page.getByLabel('Context url reference').fill(`https://idhub.pangea.org/context/${credential}.jsonld`);
        await page.getByRole('button', { name: 'Save' }).click();

        // import data
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        //await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        // TODO template is only for course credential
        //   TODO this is wrong!!
        //await page.getByLabel('Select one template for render to Pdf').selectOption('1');
        // TODO verify
        await page.getByLabel('Schema').selectOption('Membership Card');
        const data_path = path.resolve(__dirname, `../../../examples/excel_examples/${credential}.xlsx`);
        await page.getByLabel('File to import').setInputFiles(data_path);
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();
    });

    test('[user] request credential by URL with schema and context', async ({ page }) => {
        await request_credential(page);
    });

});
