import { test } from '@playwright/test';
import path from 'path';
import { login, accept_data_protection, set_org_key } from './helpers/flows';
import { TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD } from './helpers/config';

const ROOT_DIR = path.resolve(__dirname, '../../../');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');
const SCHEMAS_DIR = path.join(ROOT_DIR, 'schemas');
const CONTEXT_DIR = path.join(ROOT_DIR, 'context');


async function initial_setup_html_eidas1(page) {
    await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
    await set_org_key(page);
    await accept_data_protection(page);
    // upload HTML template (for course-credential)
    ////
    await page.getByRole('link', { name: ' Templates' }).click();
    await page.getByRole('link', { name: 'Templates PDF' }).click();
    await page.getByRole('link', { name: 'Upload new template ' }).click();
    await page.getByPlaceholder('Name').fill(`course-credential-template`);
    await page.getByLabel('Data').setInputFiles(path.join(EXAMPLES_DIR, 'course-credential_es.html'));
    await page.getByRole('button', { name: 'Save' }).click();

    await page.getByRole('link', { name: ' Credentials' }).click();
    await page.getByRole('link', { name: 'View credentials' }).click();
    await page.getByRole('link', { name: 'Organization\'s wallet' }).click();
    // upload eIDAS1 key
    ////
    await page.getByRole('link', { name: 'Manage Identities' }).click();
    await page.getByRole('link', { name: 'Add identity eIDAS1 ' }).click();
    await page.getByPlaceholder('Label').fill('mykey');
    await page.getByPlaceholder('Password of certificate').fill('123456');
    await page.getByLabel('File import').setInputFiles(path.join(EXAMPLES_DIR, 'signerDNIe004.pfx'));
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

        await page.getByLabel('Schema to import').setInputFiles(path.join(SCHEMAS_DIR, `${credential}.json`));
        await page.getByLabel('Context to import (optional)').setInputFiles(path.join(CONTEXT_DIR, `${credential}.jsonld`));
        await page.getByRole('button', { name: 'Save' }).click();

        // import data
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        await page.getByLabel('Select one template for render to Pdf').selectOption('1');
        await page.getByLabel('Schema').selectOption('NGO Course Credential Schema');

        await page.getByLabel('File to import').setInputFiles(path.join(EXAMPLES_DIR, `excel_examples/${credential}.xlsx`));
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
        await page.getByLabel('Schema to import').setInputFiles(path.join(SCHEMAS_DIR, `${credential}.json`));
        await page.getByRole('button', { name: 'Save' }).click();
        // import data
        await page.getByRole('link', { name: ' Data' }).click();
        await page.getByRole('link', { name: 'Import data ' }).click();
        //await page.getByLabel('Signature with Eidas1').selectOption('signerDNIe004.pfx');
        // TODO template is only for course credential
        //await page.getByLabel('Select one template for render to Pdf').selectOption('1');
        await page.getByLabel('Schema').selectOption('Credencial de Vulnerabilitat Financera');
        await page.getByLabel('File to import').setInputFiles(path.join(EXAMPLES_DIR, `excel_examples/${credential}.xlsx`));
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();
    });
8
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
        await page.getByLabel('File to import').setInputFiles(path.join(EXAMPLES_DIR, `excel_examples/${credential}.xlsx`));
        await page.getByRole('button', { name: 'Save' }).click();
        await page.getByRole('link', { name: '', exact: true }).click();
    });

    test.only('[user] request credential by URL with schema and context', async ({ page }) => {
        await request_credential(page);
    });

});
