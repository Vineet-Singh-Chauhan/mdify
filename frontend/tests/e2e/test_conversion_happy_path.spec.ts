import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Happy Path: Upload → Convert → Download', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('SPA loads with drop zone visible', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('mdify');
    await expect(page.locator('#drop-zone')).toBeVisible();
  });

  test('Output mode toggle changes selection', async ({ page }) => {
    await page.locator('#output-mode-package').click();
    await expect(page.locator('#output-mode-package')).toHaveClass(/bg-accent/);
    await page.locator('#output-mode-standalone').click();
    await expect(page.locator('#output-mode-standalone')).toHaveClass(/bg-accent/);
  });

  test('File input accepts supported file types', async ({ page }) => {
    const fileInput = page.locator('#file-input');
    const acceptAttr = await fileInput.getAttribute('accept');
    expect(acceptAttr).toContain('.pdf');
    expect(acceptAttr).toContain('.docx');
    expect(acceptAttr).toContain('.csv');
  });

  test('Convert button is visible after file selection', async ({ page }) => {
    // Use a real txt file for upload test
    const filePath = path.resolve(__dirname, 'fixtures/sample.txt');
    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles(filePath);
    await expect(page.locator('#convert-btn')).toBeVisible();
  });
});
