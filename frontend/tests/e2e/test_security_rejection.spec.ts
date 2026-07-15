import { test, expect } from '@playwright/test';

test.describe('Security: Spoofed file rejection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3000');
  });

  test('Error state is displayed and user message is generic', async ({ page }) => {
    // This test mocks the API response to simulate a security rejection
    await page.route('/api/v1/upload', route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'The uploaded file could not be validated. Please check the file and try again.',
        }),
      });
    });

    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles({
      name: 'malware.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('MZ\x00\x00'),  // EXE magic in PDF wrapper
    });

    await page.locator('#convert-btn').click();

    // Error alert must be visible
    const alert = page.locator('[role="alert"]');
    await expect(alert).toBeVisible();

    // Message must not contain internal details
    const text = await alert.textContent();
    expect(text).not.toContain('MagicNumberMismatchError');
    expect(text).not.toContain('stack trace');
    expect(text).not.toContain('clamd');
    expect(text?.toLowerCase()).not.toContain('exception');
  });

  test('DOCX spoofing error is displayed with generic user message', async ({ page }) => {
    await page.route('/api/v1/upload', route => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'The uploaded file could not be validated. Please check the file and try again.',
        }),
      });
    });

    const fileInput = page.locator('#file-input');
    await fileInput.setInputFiles({
      name: 'malware.docx',
      mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      buffer: Buffer.from('MZ\x00\x00'),  // EXE magic in DOCX wrapper
    });

    await page.locator('#convert-btn').click();

    const alert = page.locator('[role="alert"]');
    await expect(alert).toBeVisible();

    const text = await alert.textContent();
    expect(text).not.toContain('MagicNumberMismatchError');
    expect(text).not.toContain('stack trace');
  });
});

