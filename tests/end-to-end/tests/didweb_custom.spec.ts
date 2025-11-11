// TODO move this tests to different files according to the feature they cover

import { test, expect } from '@playwright/test';
import path from 'path';

import { login, accept_data_protection, set_org_key } from './helpers/flows';
import {TEST_DOMAIN, TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD} from './helpers/config'

test('didwebs custom', async ({ page }) => {
    test.setTimeout(0)
    await login(page, TEST_ADMIN_USER, TEST_ADMIN_PASSWD);
    await set_org_key(page);
    await accept_data_protection(page);

    await page.getByRole('link', { name: ' Credentials' }).click();
    await page.getByRole('link', { name: 'Organization\'s wallet' }).click();
    await page.getByRole('link', { name: 'Manage Identities' }).click();
    await page.getByRole('link', { name: 'Add DID identity ' }).click();
    await page.getByRole('textbox', { name: 'Label' }).fill('test1');
    await page.getByRole('button', { name: 'Save' }).click();
    //const page1Promise = page.waitForEvent('popup');
    //await page.getByRole('link', { name: 'did:web:localhost:NBCT6w' }).click();
    //const page1 = await page1Promise;
    await page.getByRole('link', { name: 'Add DID identity ' }).click();
    await page.getByRole('textbox', { name: 'Label' }).fill('test2');
    await page.getByRole('textbox', { name: 'Did' }).fill(`did:web:${TEST_DOMAIN}:test2`);
    await page.getByRole('button', { name: 'Save' }).click();
    //const page2Promise = page.waitForEvent('popup');
    //await page.getByRole('link', { name: 'did:web:localhost:test2' }).click();
    //const page2 = await page2Promise;
    await page.getByRole('link', { name: 'Add DID identity ' }).click();
    await page.getByRole('textbox', { name: 'Label' }).fill('test3');
    await page.getByRole('textbox', { name: 'Did' }).fill('did:web:ereuse.org:test3');
    await page.getByRole('button', { name: 'Save' }).click();
    //const page3Promise = page.waitForEvent('popup');
    //const downloadPromise = page.waitForEvent('download');
    //await page.getByRole('link', { name: 'did:web:ereuse.org:test3' }).click();
    //const page3 = await page3Promise;
    //const download = await downloadPromise;
    await page.getByRole('link', { name: 'Add DID identity ' }).click();
    await page.getByRole('textbox', { name: 'Label' }).fill('test4');
    await page.getByLabel('Type').selectOption('2');
    await page.getByRole('button', { name: 'Save' }).click();
});
