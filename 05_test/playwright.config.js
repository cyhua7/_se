const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:3000'
  },
  webServer: {
    command: 'node src/server.js',
    url: 'http://localhost:3000/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 10000
  }
});
