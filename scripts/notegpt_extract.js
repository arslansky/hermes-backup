const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2] || 'https://youtu.be/VoxL_YmHR-I';
  
  console.log('🎬 Starting NoteGPT transcript extraction...');
  console.log('📎 URL:', url);
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();
  
  try {
    // Go to NoteGPT
    console.log('🌐 Opening NoteGPT...');
    await page.goto('https://notegpt.io/youtube-to-text', { waitUntil: 'networkidle', timeout: 60000 });
    
    // Wait for input field and enter URL
    console.log('⌨️ Entering YouTube URL...');
    await page.waitForSelector('input[placeholder*="YouTube"], input[type="url"], textarea', { timeout: 30000 });
    const input = await page.locator('input[placeholder*="YouTube"], input[type="url"], textarea').first();
    await input.fill(url);
    
    // Click generate button
    console.log('🚀 Clicking Generate Transcript...');
    const button = await page.locator('button:has-text("Generate"), button:has-text("Transcript"), button:has-text("Start"), .generate-btn, [class*="generate"]').first();
    await button.click();
    
    // Wait for transcript to load (30-45 seconds)
    console.log('⏳ Waiting for transcript generation (45s)...');
    await page.waitForTimeout(45000);
    
    // Try to extract transcript text
    console.log('📄 Extracting transcript...');
    
    // Look for transcript content
    const transcriptSelectors = [
      '[class*="transcript"]',
      '[class*="subtitle"]',
      '[class*="text-content"]',
      '.content',
      '#transcript',
      '.transcript-text',
      'article',
      '.result'
    ];
    
    let transcript = '';
    for (const selector of transcriptSelectors) {
      const elements = await page.locator(selector).all();
      for (const el of elements) {
        const text = await el.textContent().catch(() => '');
        if (text && text.length > 200) {
          transcript = text;
          break;
        }
      }
      if (transcript) break;
    }
    
    // If no transcript found, try getting all text from main content area
    if (!transcript) {
      const bodyText = await page.locator('body').textContent();
      // Filter out UI text and keep likely transcript content
      const lines = bodyText.split('\n').filter(l => l.trim().length > 50);
      transcript = lines.join('\n');
    }
    
    if (transcript && transcript.length > 100) {
      console.log('\n=== TRANSCRIPT ===\n');
      console.log(transcript.substring(0, 50000)); // Limit output
      console.log('\n=== END TRANSCRIPT ===\n');
      console.log('✅ Transcript extracted successfully!');
      console.log('📊 Length:', transcript.length, 'characters');
    } else {
      console.log('❌ No transcript found. Page content:');
      console.log(await page.title());
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    // Take screenshot for debugging
    await page.screenshot({ path: '/root/.openclaw/workspace/notegpt_error.png' });
    console.log('📸 Screenshot saved to notegpt_error.png');
  } finally {
    await browser.close();
  }
})();
