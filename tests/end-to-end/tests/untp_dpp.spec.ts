import { test, expect } from '@playwright/test';
import path from 'path';
import { login, accept_data_protection, set_org_key } from './helpers/flows';
import { TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD } from './helpers/config';

// TODO: Update these paths to match your local project structure
const ROOT_DIR = path.resolve(__dirname, '../../../');
const SCHEMAS_DIR = path.join(ROOT_DIR, 'schemas');
const CONTEXT_DIR = path.join(ROOT_DIR, 'context');
const EXAMPLES_DIR = path.join(ROOT_DIR, 'examples');

test.describe.serial('Digital Product Passport (DPP) Workflow', () => {
    test.describe.configure({ timeout: 0 });

    test.beforeEach(async ({ page }) => {
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
        await set_org_key(page);
        await accept_data_protection(page);
    });

    test('[admin] upload UNTP schema and context', async ({ page }) => {
        await page.getByRole('link', { name: ' Templates' }).click();
        await page.getByRole('link', { name: 'Schemas' }).click();
        await page.getByRole('link', { name: 'Upload template ' }).click();
        await page.getByRole('button', { name: 'Enable from File' }).click();

        // upload schema
        await page.getByLabel('Schema to import').setInputFiles(path.join(SCHEMAS_DIR, 'DigitalProductPassport.json'));
        await page.getByLabel('Context to import (optional)').setInputFiles(path.join(CONTEXT_DIR, 'vocabulary.uncefact.org.jsonld'));
        await page.getByRole('button', { name: 'Save' }).click();


        await expect(page.locator('.alert-success')).toBeVisible();
    });

    test('[admin] issue a Digital Product Passport', async ({ page }) => {
        await page.getByRole('link', { name: ' Credentials' }).click();
        await page.getByRole('link', { name: 'UNTP credentials' }).click();

        await page.pause();
        await page.getByLabel('Issuer DID').selectOption({ index: 1 });
        await page.getByLabel('UNTP schema').selectOption({ label: 'DigitalProductPassport.json' });

        // upload payload
        await page.getByLabel('Upload object DIDs file').setInputFiles(path.join(EXAMPLES_DIR, 'DigitalProductPassport_instance.json'));

        await page.getByLabel('Create object DID?').check();
        await page.getByLabel('Select DID method').selectOption('Web');

        await page.getByLabel('Service Endpoint').fill('https://localhost/example/test_dpp_endpoint');

        // submit
        await page.getByRole('button', { name: 'Issue Credential' }).click();
        await expect(page.locator('.alert-success')).toContainText('UNTP credential issued successfully');
    });

    test.only('[public] verify the issued DPP credential', async ({ page }) => {
        const signedCredentialPath = path.join(EXAMPLES_DIR, 'sample-digital-product-passport-v0.7.0.json');

        await page.goto(`${TEST_SITE}/verify/`);
        await page.locator('#file-input').setInputFiles(signedCredentialPath);

        await page.getByRole('button', { name: 'Verify Credential' }).click();

        await expect(page.locator('#results-heading')).toContainText('Verification Successful');
    });
});
