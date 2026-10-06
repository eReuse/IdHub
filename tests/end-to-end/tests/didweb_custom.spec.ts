import { test } from '@playwright/test';
import { login, accept_data_protection, set_org_key } from './helpers/flows';
import { TEST_DOMAIN, TEST_ADMIN_USER, TEST_ADMIN_PASSWD } from './helpers/config';

test.describe('DID Identities Management', () => {
    test.describe.configure({ timeout: 0 });

    test.beforeEach(async ({ page }) => {
        await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
        await set_org_key(page);
        await accept_data_protection(page);

        await page.getByRole('link', { name: ' Credentials' }).click();
        await page.getByRole('link', { name: 'Organization\'s wallet' }).click();
        await page.getByRole('link', { name: 'Manage Identities' }).click();
    });

    test('create custom didwebs', async ({ page }) => {
        const identitiesToCreate = [
            { label: 'test1' },
            { label: 'test2', did: `did:web:${TEST_DOMAIN}:test2` },
            { label: 'test3', did: 'did:web:ereuse.org:test3' },
            { label: 'test4', type: '2' }
        ];

        for (const identity of identitiesToCreate) {
            await page.getByRole('link', { name: 'Add DID identity ' }).click();
            await page.getByRole('textbox', { name: 'Label' }).fill(identity.label);

            if (identity.did) {
                await page.getByRole('textbox', { name: 'Did' }).fill(identity.did);
            }
            if (identity.type) {
                await page.getByLabel('Type').selectOption(identity.type);
            }

            await page.getByRole('button', { name: 'Save' }).click();
        }
    });
});
