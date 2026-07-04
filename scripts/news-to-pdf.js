const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// 讀取新聞內容
const newsContent = fs.readFileSync('news-digest-2026-06-09.txt', 'utf8');

// 解析新聞內容
function parseNews(content) {
    const articles = [];
    const sections = content.split(/={40,}/);
    
    for (let i = 1; i < sections.length; i++) {
        const section = sections[i].trim();
        if (!section || section.includes('END OF DIGEST')) continue;
        
        // 解析標題行
        const lines = section.split('\n');
        const headerMatch = lines[0].match(/\[(\d+)\]\s*(.+?)\s*—\s*(.+)/);
        
        if (headerMatch) {
            const title = headerMatch[2].trim();
            const source = headerMatch[3].trim();
            
            // 提取來源URL
            const sourceLine = lines.find(l => l.startsWith('Source:'));
            const url = sourceLine ? sourceLine.replace('Source:', '').trim() : '';
            
            // 提取日期
            const dateLine = lines.find(l => l.startsWith('Date:'));
            const date = dateLine ? dateLine.replace('Date:', '').trim() : '';
            
            // 提取內容（在空行之後）
            let contentStart = false;
            let content = [];
            for (const line of lines) {
                if (contentStart && line.trim()) {
                    content.push(line.trim());
                }
                if (line.startsWith('Date:')) {
                    contentStart = true;
                }
            }
            
            articles.push({
                title,
                source,
                url,
                date,
                content: content.join('\n')
            });
        }
    }
    
    return articles;
}

// 生成 HTML
function generateHTML(articles) {
    const articleHTML = articles.map((article, index) => `
        <article class="news-article">
            <header class="article-header">
                <div class="article-meta">
                    <span class="article-number">${String(index + 1).padStart(2, '0')}</span>
                    <span class="article-source">${article.source}</span>
                    <span class="article-date">${article.date}</span>
                </div>
                <h2 class="article-title">${article.title}</h2>
            </header>
            <div class="article-content">
                ${article.content.split('\n').map(p => `<p>${p}</p>`).join('')}
            </div>
            ${article.url ? `<footer class="article-footer">
                <a href="${article.url}" class="article-link">${article.url}</a>
            </footer>` : ''}
        </article>
    `).join('');

    return `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>每日新聞摘要</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');
        
        :root {
            --primary: #1a1a2e;
            --secondary: #16213e;
            --accent: #e94560;
            --text: #333;
            --text-light: #666;
            --bg: #f5f5f5;
            --card-bg: #fff;
            --border: #e0e0e0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Noto Sans SC', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            font-size: 11pt;
        }
        
        .container {
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
        }
        
        /* 封面 */
        .cover {
            page-break-after: always;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            margin: -20mm;
            padding: 20mm;
        }
        
        .cover-title {
            font-family: 'Noto Serif SC', serif;
            font-size: 42pt;
            font-weight: 700;
            margin-bottom: 20px;
            letter-spacing: 0.1em;
        }
        
        .cover-subtitle {
            font-size: 16pt;
            font-weight: 300;
            opacity: 0.9;
            margin-bottom: 40px;
        }
        
        .cover-date {
            font-size: 14pt;
            opacity: 0.7;
            border-top: 1px solid rgba(255,255,255,0.3);
            padding-top: 20px;
            margin-top: 20px;
        }
        
        .cover-stats {
            display: flex;
            gap: 40px;
            margin-top: 60px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-number {
            font-size: 36pt;
            font-weight: 700;
            color: var(--accent);
        }
        
        .stat-label {
            font-size: 10pt;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        /* 目錄 */
        .toc {
            page-break-after: always;
            padding: 40px 0;
        }
        
        .toc-title {
            font-family: 'Noto Serif SC', serif;
            font-size: 24pt;
            margin-bottom: 30px;
            color: var(--primary);
            border-bottom: 3px solid var(--accent);
            padding-bottom: 10px;
        }
        
        .toc-list {
            list-style: none;
        }
        
        .toc-item {
            display: flex;
            align-items: baseline;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
            transition: all 0.3s;
        }
        
        .toc-item:hover {
            background: rgba(233, 69, 96, 0.05);
            padding-left: 10px;
        }
        
        .toc-number {
            font-size: 18pt;
            font-weight: 700;
            color: var(--accent);
            min-width: 40px;
        }
        
        .toc-text {
            flex: 1;
        }
        
        .toc-article-title {
            font-weight: 500;
            font-size: 12pt;
        }
        
        .toc-article-source {
            font-size: 9pt;
            color: var(--text-light);
            margin-top: 2px;
        }
        
        /* 文章 */
        .news-article {
            page-break-inside: avoid;
            margin-bottom: 40px;
            background: var(--card-bg);
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid var(--accent);
        }
        
        .article-header {
            margin-bottom: 20px;
        }
        
        .article-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            font-size: 9pt;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .article-number {
            background: var(--accent);
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 10pt;
        }
        
        .article-title {
            font-family: 'Noto Serif SC', serif;
            font-size: 18pt;
            font-weight: 600;
            color: var(--primary);
            line-height: 1.4;
        }
        
        .article-content {
            font-size: 11pt;
            line-height: 1.8;
            color: var(--text);
        }
        
        .article-content p {
            margin-bottom: 12px;
            text-align: justify;
        }
        
        .article-content p:first-child::first-letter {
            font-size: 24pt;
            font-weight: 700;
            color: var(--accent);
            float: left;
            line-height: 1;
            margin-right: 8px;
            margin-top: 4px;
        }
        
        .article-footer {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid var(--border);
            font-size: 8pt;
        }
        
        .article-link {
            color: var(--text-light);
            text-decoration: none;
            word-break: break-all;
        }
        
        /* 分類標籤 */
        .category-tag {
            display: inline-block;
            padding: 4px 12px;
            background: var(--secondary);
            color: white;
            border-radius: 20px;
            font-size: 8pt;
            font-weight: 500;
            margin-right: 8px;
        }
        
        /* 頁首頁尾 */
        @page {
            margin: 15mm;
            @top-center {
                content: "每日新聞摘要";
                font-size: 9pt;
                color: #999;
            }
            @bottom-center {
                content: counter(page);
                font-size: 9pt;
                color: #999;
            }
        }
        
        @page :first {
            @top-center { content: none; }
            @bottom-center { content: none; }
        }
        
        /* 響應式 */
        @media screen {
            .container {
                max-width: 800px;
                padding: 40px 20px;
            }
            
            .cover {
                height: auto;
                min-height: 80vh;
                border-radius: 12px;
                margin-bottom: 40px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 封面 -->
        <div class="cover">
            <h1 class="cover-title">每日新聞摘要</h1>
            <p class="cover-subtitle">Daily News Digest</p>
            <p class="cover-date">2026年6月9日</p>
            <div class="cover-stats">
                <div class="stat-item">
                    <div class="stat-number">10</div>
                    <div class="stat-label">篇文章</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">7</div>
                    <div class="stat-label">個來源</div>
                </div>
            </div>
        </div>
        
        <!-- 目錄 -->
        <div class="toc">
            <h2 class="toc-title">目錄 Contents</h2>
            <ul class="toc-list">
                ${articles.map((article, index) => `
                <li class="toc-item">
                    <span class="toc-number">${String(index + 1).padStart(2, '0')}</span>
                    <div class="toc-text">
                        <div class="toc-article-title">${article.title}</div>
                        <div class="toc-article-source">${article.source} · ${article.date}</div>
                    </div>
                </li>
                `).join('')}
            </ul>
        </div>
        
        <!-- 文章內容 -->
        ${articleHTML}
    </div>
</body>
</html>`;
}

// 主函數
async function main() {
    try {
        // 解析新聞
        const articles = parseNews(newsContent);
        console.log(`解析到 ${articles.length} 篇文章`);
        
        // 生成 HTML
        const html = generateHTML(articles);
        fs.writeFileSync('news-output.html', html);
        console.log('HTML 已生成: news-output.html');
        
        // 生成 PDF
        const browser = await puppeteer.launch({
            executablePath: '/root/.cache/puppeteer/chrome/linux-149.0.7827.115/chrome-linux64/chrome',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        
        await page.setContent(html, {
            waitUntil: 'networkidle0'
        });
        
        await page.pdf({
            path: 'news-digest.pdf',
            format: 'A4',
            printBackground: true,
            margin: {
                top: '15mm',
                right: '15mm',
                bottom: '15mm',
                left: '15mm'
            }
        });
        
        await browser.close();
        console.log('PDF 已生成: news-digest.pdf');
        
    } catch (error) {
        console.error('錯誤:', error);
    }
}

main();
