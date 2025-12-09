// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';
import path from 'path';

import { login, accept_data_protection, set_org_key } from './helpers/flows';
import {TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD} from './helpers/config'

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
    await page.getByRole('button', { name: 'Enable from URL' }).click();
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
