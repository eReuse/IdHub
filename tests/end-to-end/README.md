> **Info**
> As of 2025-04-02, from the 20 end-to-end tests, 4 are failing, we hope to fix it soon

## Quickstart

This section runs [end-to-end tests](https://en.wikipedia.org/wiki/System_testing) using [playwright](https://playwright.dev)

Once [playwright is installed](https://playwright.dev/docs/intro#installing-playwright) run all the tests with `./run.sh`, by default, it assumes that a docker deployment (`./docker-reset.sh`) is running in http://127.0.0.1:8001

## Developer

When introducing a new test, use `.only` temporarily to just enable that test

```js
test.only('NEW example', async ({ page }) => {
    await login(page);
    test.setTimeout(0)
    await page.pause();
});
```
