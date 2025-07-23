// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';

import path from 'path';

// TEMP
//const TEST_SITE = process.env.TEST_SITE || 'http://127.0.0.1:9001'
const TEST_SITE = process.env.TEST_SITE || 'https://lab7.ereuse.org'

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


async function login(page, user, password) {
    await page.goto(`${TEST_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(user);
    await page.getByPlaceholder('Password').fill(password);
    await page.getByPlaceholder('Password').press('Enter');
}

// https://stackoverflow.com/questions/73338339/playwright-framework-is-there-a-way-we-can-execute-dependent-tests-in-playwrig

test.describe.serial("dynamic template tour", ()=> {
    let skip_user_test = false;
    test('admin', async ({ page }) => {
        test.setTimeout(0)
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        await set_org_key(page);

        await accept_data_protection(page);

        // DEBUG
        await page.pause()

        // borra el esquema del curso si existe
        ////
        await page.getByRole('link', { name: ' Templates' }).click();
        const course_credential_visible = await page.getByRole('cell', { name: 'course-credential.json' }).isVisible();
        const delete_button = await page.getByRole('row', { name: 'course-credential' }).getByRole('link').nth(2);
        const delete_button_visible = await delete_button.isVisible();
        if (course_credential_visible) {
            if (delete_button_visible) {
                await delete_button.click();
                await page.getByRole('link', { name: 'Delete' }).click();
            } else {
                console.log('course-credential.json cannot be removed. Test cannot continue. Reset instance.')
                skip_user_test = true
                test.skip();
            }
        }

        // sube esquema curso por fichero
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable Schema from File' }).click();
        const schema_path = path.resolve(__dirname, '../../../schemas/course-credential.json');
        await page.getByLabel('Schema to import').setInputFiles(schema_path);
        const context_path = path.resolve(__dirname, '../../../context/course-credential.jsonld');
        await page.getByLabel('Context to import (optional)').setInputFiles(context_path);
        await page.getByRole('button', { name: 'Save' }).click(context_path);


        // esto fue un fallo
        //await page.getByRole('link', { name: ' Data' }).click();
        //await page.getByRole('link', { name: 'Import data ' }).click();

        // subida de plantilla
        ////
        await page.getByRole('link', { name: ' Credentials' }).click();
        await page.getByRole('link', { name: 'Templates Pdf' }).click();
        await page.getByRole('link', { name: 'Upload new template ' }).click();
        await page.getByPlaceholder('Name').click();
        await page.getByPlaceholder('Name').fill('course-template');
        const cred_path = path.resolve(__dirname, '../../../examples/course-credential_es.html');
        await page.getByLabel('Data').setInputFiles(cred_path);
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: 'View credentials' }).click();
        await page.getByRole('link', { name: 'Organization\'s wallet' }).click();

        // subida de plantilla
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
        await page.getByRole('link', { name: ' Credentials' }).click();

        // // subida de eidas1
        // ////
        // await page.getByRole('link', { name: 'Data' }).click();
        // await page.getByRole('link', { name: 'Import data' }).click();
        // await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        // await page.getByLabel('Select one template for').selectOption('1');
        // await page.getByLabel('Schema').selectOption('7');

        // intento de descargar el excel, descartado
        //await page.getByRole('link', { name: ' Templates' }).click();
        //const downloadPromise = page.waitForEvent('download');
        //await page.getByRole('row', { name: '07/09/2025 1 p.m. course-' }).getByRole('link').first().click();
        //const download = await downloadPromise;

        // data import con excel example
        ////

        // visibility problem on small screens
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        await page.getByLabel('Select one template for').selectOption('1');
        await page.getByLabel('Schema').selectOption('7');
        const data_path = path.resolve(__dirname, '../../../examples/excel_examples/course-credential.xlsx');
        await page.getByLabel('File to import').setInputFiles(data_path);
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();

        // DEBUG
        await page.pause()
    });

    // TEMP disable it
    test('user', async ({ page }) => {
        test.skip( skip_user_test == true )
        test.setTimeout(0)

        // login como usuario
        ////
        await login(page, TEST_USER, TEST_USER_PASSWD);
        await accept_data_protection(page);

        //await page.getByPlaceholder('Password').click();
        //await page.getByPlaceholder('Password').fill('1234');
        //await page.getByRole('button', { name: 'Log in' }).click();
        //await page.locator('#id_accept_privacy').check();
        //await page.locator('#id_accept_legal').check();
        //await page.locator('#id_accept_cookies').check();
        //await page.getByRole('link', { name: 'Confirm' }).click();

        // request credential
        ////
        await page.getByRole('link', { name: 'Request a credential' }).click();
        await page.getByRole('button', { name: 'Request' }).click();
        await page.getByRole('link', { name: '' }).click();
        // click pdf y click json
        ////
        const download1Promise = page.waitForEvent('download');
        await page.getByRole('link', { name: 'Download as JSON' }).click();
        const download1 = await download1Promise;
        const download2Promise = page.waitForEvent('download');
        await page.getByRole('link', { name: 'Download as PDF' }).click();
        const download2 = await download2Promise;
    });
});
