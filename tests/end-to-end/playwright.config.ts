import { defineConfig, devices } from '@playwright/test';

const VIDEO = process.env.VIDEO === 'on';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
// require('dotenv').config();

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  //workers: process.env.CI ? 1 : undefined,
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    // https://github.com/microsoft/playwright/issues/10855
    viewport: { width: 1280, height: 720},
    //video: VIDEO === 'on' ? 'on' : 'off',
    // thanks https://www.youtube.com/watch?v=ETFS_RMt4go
    // https://playwright.dev/docs/test-use-options#more-browser-and-context-options
    // Conditionally add slowMo when video is on:
    ...(VIDEO && {
      video: {
        mode: 'on',
        // but remember that video quality is not a priority https://github.com/microsoft/playwright/issues/12056
        size: { width: 1280, height: 720},
      },
      launchOptions: {
        slowMo: 1000, // 1 second delay between each operation
      //  slowMo: 0, // 1 second delay between each operation
      },
    }),
    recordVideo: { dir: 'test-results/videos/' },
    /* Base URL to use in actions like `await page.goto('/')`. */
    // baseURL: 'http://127.0.0.1:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  // viewport needs to be configured for each browser, see https://github.com/microsoft/playwright/issues/13673#issuecomment-1105621745
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'],
          viewport: { width: 1280, height: 720 },
      }
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'],
          viewport: { width: 1280, height: 720 },
      }
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'],
          viewport: { width: 1280, height: 720 },
      }
    },

    /* Test against mobile viewports. */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'npm run start',
  //   url: 'http://127.0.0.1:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
