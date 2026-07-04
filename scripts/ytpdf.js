#!/usr/bin/env node
/**
 * YTPDF Workflow - YouTube to PDF Report Generator
 * Fixed location: /root/.openclaw/workspace/tools/ytpdf.js
 * 
 * Usage: node ytpdf.js <youtube_url> [output_name]
 * Example: node ytpdf.js "https://youtu.be/VoxL_YmHR-I" "MyReport"
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Config
const WORKSPACE = '/root/.openclaw/workspace';
const OUTPUT_DIR = WORKSPACE;

// Filler words to remove
const FILLER_WORDS = ['uh', 'um', 'like', 'right', 'so', 'you know', 'i mean', 'basically', 'literally'];

async function extractTranscript(youtubeUrl) {
  console.log('🎬 Starting NoteGPT transcript extraction...');
  console.log('📎 URL:', youtubeUrl);
  
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
    await page.waitForSelector('input[placeholder*="Paste the YouTube video link"], input[placeholder*="YouTube"], input[type="url"], textarea', { timeout: 30000 });
    const input = await page.locator('input[placeholder*="Paste the YouTube video link"], input[placeholder*="YouTube"], input[type="url"], textarea').first();
    await input.fill(youtubeUrl);
    
    // Click generate button
    console.log('🚀 Clicking Generate Transcript...');
    const button = await page.locator('button:has-text("Generate Transcript"), button:has-text("Generate"), button:has-text("Transcript"), .generate-btn, [class*="generate"]').first();
    await button.click();
    
    // Wait for transcript to load (up to 60 seconds)
    console.log('⏳ Waiting for transcript generation (60s)...');
    await page.waitForTimeout(60000);
    
    // Wait for specific transcript elements to appear
    console.log('🔍 Looking for transcript content...');
    try {
      await page.waitForSelector('.transcript-content, .result-content, [class*="transcript"], [class*="result"]', { timeout: 30000 });
    } catch (e) {
      console.log('⚠️ Transcript selector not found, trying fallback...');
    }
    
    // Extract transcript text
    console.log('📄 Extracting transcript...');
    
    // Look for transcript content with more specific selectors based on UI
    const transcriptSelectors = [
      '.transcript-content',
      '[class*="transcript-text"]',
      '[class*="transcript-content"]',
      '[class*="result-text"]',
      '[class*="text-content"]',
      '.content',
      '#transcript',
      '.transcript-text',
      'article',
      '.result',
      '.output',
      '[class*="output"]',
      // NoteGPT specific selectors
      '[data-testid*="transcript"]',
      '[role="tabpanel"]',
      '.tab-content',
      '[class*="tab-panel"]'
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
    
    // Fallback: get all text from main content area
    if (!transcript) {
      const bodyText = await page.locator('body').textContent();
      const lines = bodyText.split('\n').filter(l => l.trim().length > 50);
      transcript = lines.join('\n');
    }
    
    await browser.close();
    
    if (transcript && transcript.length > 100) {
      console.log('✅ Transcript extracted successfully!');
      console.log('📊 Length:', transcript.length, 'characters');
      return transcript;
    } else {
      throw new Error('No transcript found or too short');
    }
    
  } catch (error) {
    await browser.close();
    console.error('❌ Error:', error.message);
    throw error;
  }
}

function cleanTranscript(text) {
  console.log('🧹 Cleaning transcript...');
  
  // Remove timestamps (e.g., [00:01:23] or 00:01:23)
  let cleaned = text.replace(/\[?\d{1,2}:\d{2}:\d{2}\]?/g, '');
  cleaned = cleaned.replace(/\d{1,2}:\d{2}/g, '');
  
  // Remove filler words (case insensitive)
  FILLER_WORDS.forEach(word => {
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    cleaned = cleaned.replace(regex, '');
  });
  
  // Remove UI/marketing text patterns - only specific patterns
  cleaned = cleaned.replace(/NoteGPT/gi, '');
  cleaned = cleaned.replace(/YouTube to Text Converter/gi, '');
  cleaned = cleaned.replace(/AI Summary/gi, '');
  cleaned = cleaned.replace(/Read More/gi, '');
  cleaned = cleaned.replace(/30% Off/gi, '');
  cleaned = cleaned.replace(/Upgrade/gi, '');
  cleaned = cleaned.replace(/NewTranscript/gi, '');
  cleaned = cleaned.replace(/SubtitlesChapter/gi, '');
  cleaned = cleaned.replace(/MediumShort/gi, '');
  cleaned = cleaned.replace(/CopyDownload/gi, '');
  cleaned = cleaned.replace(/🚀/g, '');
  
  // Remove JavaScript code blocks - only if they start with specific patterns
  cleaned = cleaned.replace(/window\.__NUXT__.*$/s, '');
  cleaned = cleaned.replace(/\[\s*"ShallowReactive".*$/s, '');
  
  // Remove UI elements text - only specific patterns
  cleaned = cleaned.replace(/Log in to get 15 free quotas per month\./g, '');
  cleaned = cleaned.replace(/Log InSummaryMind MapAI ChatMoreSummarize/g, '');
  cleaned = cleaned.replace(/Copy TranscriptDownload Transcript/g, '');
  cleaned = cleaned.replace(/Generate Infographic HotGenerate PodcastGenerate PresentationGenerate QuizGenerate Flashcards/g, '');
  cleaned = cleaned.replace(/Install YouTube Extension for Free/g, '');
  
  // Remove extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  
  console.log('✅ Cleaned transcript');
  return cleaned;
}

function generateSummary(transcript) {
  console.log('📝 Generating summary structure...');
  
  // Split into sentences/paragraphs
  const sentences = transcript.split(/[.!?。！？]+/).filter(s => s.trim().length > 20);
  
  // Extract key points (first sentence of each paragraph-like chunk)
  const chunkSize = Math.max(5, Math.floor(sentences.length / 8));
  const keyPoints = [];
  
  for (let i = 0; i < sentences.length; i += chunkSize) {
    const chunk = sentences.slice(i, i + chunkSize).join('. ');
    if (chunk.length > 50) {
      keyPoints.push(chunk.substring(0, 200) + (chunk.length > 200 ? '...' : ''));
    }
  }
  
  return {
    fullText: transcript,
    keyPoints: keyPoints.slice(0, 10),
    wordCount: transcript.split(/\s+/).length,
    charCount: transcript.length
  };
}

async function generatePDF(summary, outputName) {
  console.log('📄 Generating PDF...');
  
  const outputPath = path.join(OUTPUT_DIR, `${outputName}.pdf`);
  
  // Simple text-based PDF generation using basic HTML -> PDF approach
  // For proper Chinese PDF, we'd need reportlab + wqy-zenhei
  // This is a simplified version - for full implementation, use Python reportlab
  
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
  h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
  h2 { color: #007acc; margin-top: 30px; }
  .meta { color: #666; font-size: 0.9em; margin-bottom: 20px; }
  .key-point { background: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 4px solid #007acc; }
  .content { text-align: justify; }
  .footer { margin-top: 40px; font-size: 0.8em; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }
</style>
</head>
<body>
  <h1>${outputName}</h1>
  <div class="meta">
    Generated: ${new Date().toLocaleString()}<br>
    Words: ${summary.wordCount} | Characters: ${summary.charCount}
  </div>
  
  <h2>🎯 Key Points</h2>
  ${summary.keyPoints.map((point, i) => `
    <div class="key-point">
      <strong>${i + 1}.</strong> ${point}
    </div>
  `).join('')}
  
  <h2>📝 Full Transcript</h2>
  <div class="content">
    ${summary.fullText.replace(/\n/g, '<br>')}
  </div>
  
  <div class="footer">
    Generated by YTPDF Workflow | NoteGPT Transcript
  </div>
</body>
</html>
  `;
  
  // Save HTML first (can be converted to PDF with browser or wkhtmltopdf)
  const htmlPath = outputPath.replace('.pdf', '.html');
  fs.writeFileSync(htmlPath, htmlContent);
  
  console.log('✅ HTML report saved:', htmlPath);
  
  // Try to generate PDF using Playwright's PDF generation
  try {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setContent(htmlContent);
    await page.pdf({ 
      path: outputPath, 
      format: 'A4',
      margin: { top: '20px', right: '20px', bottom: '20px', left: '20px' }
    });
    await browser.close();
    console.log('✅ PDF saved:', outputPath);
    return outputPath;
  } catch (error) {
    console.log('⚠️ PDF generation failed, HTML version available:', htmlPath);
    return htmlPath;
  }
}

async function main() {
  const youtubeUrl = process.argv[2];
  const outputName = process.argv[3] || `YT_Report_${Date.now()}`;
  
  if (!youtubeUrl) {
    console.log('Usage: node ytpdf.js <youtube_url> [output_name]');
    console.log('Example: node ytpdf.js "https://youtu.be/VoxL_YmHR-I" "MyReport"');
    process.exit(1);
  }
  
  console.log('╔════════════════════════════════════╗');
  console.log('║     YTPDF Workflow Started         ║');
  console.log('╚════════════════════════════════════╝');
  console.log();
  
  try {
    // Step 1: Extract transcript
    const rawTranscript = await extractTranscript(youtubeUrl);
    
    // Step 2: Clean transcript
    const cleanedTranscript = cleanTranscript(rawTranscript);
    
    // Step 3: Generate summary
    const summary = generateSummary(cleanedTranscript);
    
    // Step 4: Generate PDF
    const outputPath = await generatePDF(summary, outputName);
    
    console.log();
    console.log('╔════════════════════════════════════╗');
    console.log('║     YTPDF Workflow Complete!       ║');
    console.log('╚════════════════════════════════════╝');
    console.log('📁 Output:', outputPath);
    console.log('📊 Stats:', summary.wordCount, 'words,', summary.charCount, 'chars');
    
  } catch (error) {
    console.error('❌ Workflow failed:', error.message);
    process.exit(1);
  }
}

main();
