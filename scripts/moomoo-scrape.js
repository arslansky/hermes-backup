const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('https://www.moomoo.com/hant/news/post/70514334', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  // Try to get article content specifically
  const articleSelectors = ['article', '[class*="article"]', '[class*="content"]', 'main', '.news-detail', '[class*="post-content"]'];
  
  for (const sel of articleSelectors) {
    const el = await page.$(sel);
    if (el) {
      const text = await el.innerText();
      if (text.length > 500) {
        console.log('FOUND_VIA:', sel);
        console.log(text);
        await browser.close();
        return;
      }
    }
  }
  
  // Fallback: body text
  const body = await page.$eval('body', el => el.innerText);
  console.log('BODY_FALLBACK:');
  console.log(body.slice(0, 5000));
  
  await browser.close();
})();
