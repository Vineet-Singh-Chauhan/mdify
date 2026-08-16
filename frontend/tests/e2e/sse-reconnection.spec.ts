import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

test('test_sse_reconnection_shows_indicator', async ({ page }) => {
  await page.goto('http://localhost:3000/');

  // Mock API endpoints
  await page.route('**/api/v1/upload', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ task_id: 'fake-task-123', original_name: 'test.pdf', output_mode: 'standalone', status: 'queued' })
    });
  });

  // 1. Initial SSE connection: immediately abort to simulate connection drop
  await page.route('**/api/v1/events/fake-task-123', async route => {
    await route.abort('failed');
  });
  
  // 2. Mock the status endpoint which the hook fetches before retrying
  await page.route('**/api/v1/tasks/fake-task-123/status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ task_id: 'fake-task-123', stage: 'PARSING', status: 'ACTIVE', original_name: 'test.pdf', output_mode: 'standalone' })
    });
  });

  // Create dummy file
  const filePath = path.join(__dirname, 'dummy.txt');
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, 'dummy content');
  }

  // Upload
  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.locator('#drop-zone').click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(filePath);
  
  await page.locator('#convert-btn').click();

  // The hook tries to connect via SSE, gets aborted, and sets isReconnecting to true
  await expect(page.getByText('Reconnecting…')).toBeVisible({ timeout: 10000 });
  
  // 3. Unroute and fulfill with SUCCESS
  await page.unroute('**/api/v1/events/fake-task-123');
  await page.route('**/api/v1/events/fake-task-123', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: `data: {"task_id": "fake-task-123", "stage": "SUCCESS", "status": "SUCCESS"}\n\n`
    });
  });

  // Hook retries after 1000ms (1s backoff for first retry), gets success, turns off isReconnecting
  await expect(page.getByText('Reconnecting…')).toBeHidden({ timeout: 10000 });
});
