import { test } from '@playwright/test';
import path from 'path';
import { login, accept_data_protection, set_org_key } from './helpers/flows';
import { TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD } from './helpers/config';

const ASSETS_DIR = path.resolve(__dirname, '../../../examples');

test.describe('Credential Templates', () => {

    test('credential without html template', async ({ page }) => {
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
        await set_org_key(page);
        await accept_data_protection(page);

        //await page.pause();
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Schemas' }).click();
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable from URL' }).click();

        await page.getByRole('textbox', { name: 'Schema url reference' }).fill('https://idhub.pangea.org/vc_schemas/course-credential.json');
        await page.getByRole('textbox', { name: 'Context url reference' }).fill('https://idhub.pangea.org/context/course-credential.jsonld');
        await page.getByRole('button', { name: 'Save' }).click();

        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        await page.getByLabel('Schema').selectOption('1');

        await page.getByLabel('File to import').setInputFiles(path.join(ASSETS_DIR, 'excel_examples/course-credential.xlsx'));
        await page.getByRole('button', { name: 'Save' }).click();

        // Logout and login as user
        await page.getByRole('link', { name: '' }).click();
        await login(page, TEST_USER, TEST_USER_PASSWD);
        await accept_data_protection(page);

        await page.getByRole('link', { name: 'Request a credential' }).click();
        await page.getByRole('button', { name: 'Request' }).click();
        await page.getByRole('link', { name: '' }).click();

        const page1Promise = page.waitForEvent('popup');
        await page.getByRole('link', { name: 'View as HTML' }).click();
        await page1Promise;

    });

    test('credential with html template', async ({ page }) => {
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);

        //await page.wait_for_load_state("load")
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Templates PDF' }).click();
        await page.getByRole('link', { name: 'Upload new template ' }).click();
        await page.goto(`${TEST_SITE}/admin/templates_pdf/new/`);

        await page.getByRole('textbox', { name: 'Name' }).fill('course');
        await page.getByLabel('Data').setInputFiles(path.join(ASSETS_DIR, 'course-credential_es.html'));
        await page.getByRole('button', { name: 'Save' }).click();

        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        await page.getByLabel('Select one template for').selectOption('1');
        await page.getByLabel('Schema').selectOption('1');
        await page.getByLabel('File to import').setInputFiles(path.join(ASSETS_DIR, 'excel_examples/course-credential.xlsx'));
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

});
