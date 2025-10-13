import {TEST_SITE, TEST_ADMIN_USER, TEST_ADMIN_PASSWD, TEST_USER, TEST_USER_PASSWD} from './config'

// optional flow (only first time per idhub service start)
export async function set_org_key(page) {
    //const encryption_key_page = page.getByText('Encryption Key')
    const encryption_key_page_admin = await page.getByRole('heading', { name: 'Encryption Key', exact: true })
    if (await encryption_key_page_admin.isVisible()) {
        await page.getByPlaceholder('Key for encrypt the secrets').click();
        await page.getByPlaceholder('Key for encrypt the secrets').fill('DEMO');
        await page.getByRole('button', { name: 'Save' }).click();
    }
}

export async function login(page, user, password) {
    await page.goto(`${TEST_SITE}/login`);
    await page.getByPlaceholder('Email address').click();
    await page.getByPlaceholder('Email address').fill(user);
    await page.getByPlaceholder('Password').fill(password);
    await page.getByPlaceholder('Password').press('Enter');
}

// optional page (decrypt)
// src https://playwright.dev/docs/locators#matching-one-of-the-two-alternative-locators
export async function accept_data_protection(page) {
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
