const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function captureAllSlides() {
  const outputDir = path.join(__dirname, 'presentation_assets', 'slide_captures');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('[1/2] Launching headless browser to capture 17 slides from interactive_presentation.html...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1.5 // 1.5x supersampling for ultra-crisp high-DPI retina rendering
  });
  const page = await context.newPage();

  const totalSlides = 17;
  const slidePaths = [];

  for (let i = 0; i < totalSlides; i++) {
    const slideUrl = `file:///${path.join(__dirname, 'interactive_presentation.html').replace(/\\/g, '/')}?slide=${i}&export=true`;
    await page.goto(slideUrl, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => {
      await document.fonts.ready;
    });
    // Brief pause to ensure all charts and SVG layers settle
    await page.waitForTimeout(300);

    const filename = `slide_${String(i + 1).padStart(2, '0')}.png`;
    const filepath = path.join(outputDir, filename);
    await page.screenshot({ path: filepath, quality: 95, type: 'jpeg' });
    slidePaths.push(filepath);
    console.log(`  ✔ Captured Slide ${i + 1}/${totalSlides}: ${filename}`);
  }

  await browser.close();
  console.log(`[2/2] Successfully captured all ${totalSlides} slides at 1920x1080 resolution in: ${outputDir}`);
}

captureAllSlides().catch(err => {
  console.error('[ERROR] Failed to capture slides:', err);
  process.exit(1);
});
