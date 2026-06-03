const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

// 加载 .env 文件
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    envContent.split('\n').forEach(line => {
        const [key, ...valueParts] = line.split('=');
        if (key && !key.startsWith('#')) {
            process.env[key.trim()] = valueParts.join('=').trim();
        }
    });
}

const PORT = process.env.PORT || 8000;
const API_KEY = process.env.ANTHROPIC_API_KEY;
const BASE_URL = process.env.BASE_URL || 'https://api.anthropic.com';
const MODEL = process.env.CLAUDE_MODEL || 'claude-sonnet-4-6';

if (!API_KEY) {
    console.error('错误：请设置环境变量 ANTHROPIC_API_KEY');
    process.exit(1);
}

console.log(`Stock Agent API 启动中...`);
console.log(`模型: ${MODEL}`);
console.log(`API 地址: ${BASE_URL}`);

// 代理配置（自动检测 Clash 端口）
const PROXY_URL = process.env.HTTPS_PROXY || process.env.HTTP_PROXY || 'http://127.0.0.1:7897';
console.log(`代理地址: ${PROXY_URL}`);

// 使用 undici 的 ProxyAgent 或者简单的代理实现
// 由于 Node.js 原生不支持代理，我们直接用 fetch 并设置环境变量

// 工具定义
const TOOL_DEFINITIONS = [
    {
        name: 'stock_quote',
        description: '查询股票实时价格和涨跌幅。使用场景：用户问"茅台现在多少钱"、"AAPL今天涨了吗"',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码，如 AAPL、600519' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'], description: '市场，默认 US' },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_kline',
        description: '获取K线数据和技术指标（MA、RSI、MACD）。使用场景：用户问"茅台最近怎么样"、"AAPL的RSI是多少"',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                period: { type: 'string', enum: ['1mo', '3mo', '6mo', '1y'], description: '时间周期，默认 1mo' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'], description: '市场，默认 US' },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_valuation',
        description: '查询估值指标（PE、PB、股息率）。使用场景：用户问"茅台估值贵不贵"、"AAPL的PE是多少"',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'], description: '市场，默认 US' },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_news',
        description: '检索股票相关新闻。使用场景：用户问"茅台最近有什么新闻"、"AAPL今天为什么涨了"',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                limit: { type: 'integer', description: '返回条数，默认 5' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'], description: '市场，默认 US' },
            },
            required: ['symbol'],
        },
    },
];

// 简化的工具执行（返回模拟数据）
function executeTool(name, params) {
    console.log(`执行工具: ${name}`, params);
    
    if (name === 'stock_quote') {
        const prices = { 'AAPL': 168.50, 'NVDA': 520.80, 'TSLA': 245.60, '600519': 1800.00, '茅台': 1800.00 };
        const names = { 'AAPL': 'Apple Inc.', 'NVDA': 'NVIDIA Corporation', 'TSLA': 'Tesla, Inc.', '600519': '贵州茅台', '茅台': '贵州茅台' };
        const symbol = params.symbol || 'AAPL';
        const upperSymbol = symbol.toUpperCase();
        const price = prices[upperSymbol] || prices[symbol] || 100;
        
        return JSON.stringify({
            symbol: symbol,
            name: names[upperSymbol] || names[symbol] || symbol,
            price: price,
            change: price * 0.02,
            change_pct: 2.0,
            volume: 2500000,
            market_cap: price * 10000000000,
            currency: symbol === '600519' || symbol === '茅台' ? 'CNY' : 'USD',
            timestamp: new Date().toISOString(),
        });
    }
    
    if (name === 'stock_kline') {
        return JSON.stringify({
            symbol: params.symbol,
            data_points: 30,
            dates: Array.from({length: 30}, (_, i) => `2024-01-${String(i+1).padStart(2, '0')}`),
            close: Array.from({length: 30}, (_, i) => 150 + Math.sin(i * 0.3) * 20),
            indicators: { MA_5: [152, 154, 153, 155, 156], RSI_14: [55, 58, 62, 60, 57] },
        });
    }
    
    if (name === 'stock_valuation') {
        return JSON.stringify({
            symbol: params.symbol,
            pe_ttm: 28.5,
            pe_forward: 25.2,
            pb: 45.2,
            dividend_yield: 0.005,
            currency: 'USD',
        });
    }
    
    if (name === 'stock_news') {
        return JSON.stringify({
            symbol: params.symbol,
            news: [
                { title: '公司业绩超预期', source: 'Reuters', date: '2024-01-10', summary: '本季度营收增长20%' },
                { title: '行业前景看好', source: 'Bloomberg', date: '2024-01-09', summary: '分析师上调目标价' },
            ],
            total_count: 2,
        });
    }
    
    return JSON.stringify({ error: 'UNKNOWN_TOOL', message: `未知工具: ${name}` });
}

// 系统提示词
const SYSTEM_PROMPT = `# 角色
你是一个专业的股票分析助手，帮助用户分析股票行情、技术指标、估值水平和相关新闻。

## 能力
你可以使用以下工具：
- stock_quote：查询实时价格和涨跌幅
- stock_kline：获取K线数据和技术指标
- stock_valuation：查询估值指标（PE、PB、股息率）
- stock_news：检索股票相关新闻

## 使用规则
1. 用户问价格相关问题 → 调用 stock_quote
2. 用户问走势/技术分析 → 调用 stock_kline
3. 用户问估值/贵不贵 → 调用 stock_valuation
4. 用户问新闻/原因 → 调用 stock_news
5. 用户问综合分析 → 多次调用工具，综合回答

## 分析方法论
- PE（市盈率）：越低越便宜，但要和行业平均对比
- PB（市净率）：PB < 1 可能被低估
- RSI > 70 超买，< 30 超卖

## 免责声明
你是一个分析工具，不是投资顾问。
- 不要给出"买入"、"卖出"、"持有"等具体建议
- 只提供数据分析和客观描述
- 提醒用户投资有风险`;

// 调用 Claude API（支持代理）
async function callClaudeAPI(messages) {
    const url = `${BASE_URL}/v1/messages`;
    
    const body = {
        model: MODEL,
        max_tokens: 4096,
        system: SYSTEM_PROMPT,
        tools: TOOL_DEFINITIONS,
        messages: messages,
    };

    console.log(`调用 Claude API: ${url}`);
    console.log(`模型: ${MODEL}`);
    console.log(`消息数: ${messages.length}`);

    // 设置代理环境变量（Node.js fetch 会使用这些）
    const originalHttpProxy = process.env.HTTP_PROXY;
    const originalHttpsProxy = process.env.HTTPS_PROXY;
    
    process.env.HTTP_PROXY = PROXY_URL;
    process.env.HTTPS_PROXY = PROXY_URL;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': API_KEY,
                'anthropic-version': '2023-06-01',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`API 错误: ${response.status}`, errorText);
            throw new Error(`API 请求失败: ${response.status} ${errorText}`);
        }

        return await response.json();
    } finally {
        // 恢复原始代理设置
        process.env.HTTP_PROXY = originalHttpProxy;
        process.env.HTTPS_PROXY = originalHttpsProxy;
    }
}

// Agent Loop
async function agentLoop(userInput, messages = []) {
    messages.push({ role: 'user', content: userInput });
    
    let loopCount = 0;
    const maxLoops = 10;

    while (loopCount < maxLoops) {
        loopCount++;
        console.log(`\nAgent Loop 第 ${loopCount} 轮`);

        try {
            const response = await callClaudeAPI(messages);
            console.log(`响应类型: ${response.stop_reason}`);

            let hasToolUse = false;
            const assistantContent = [];

            for (const block of response.content) {
                assistantContent.push(block);

                if (block.type === 'tool_use') {
                    hasToolUse = true;
                    console.log(`工具调用: ${block.name}`);

                    const toolResult = executeTool(block.name, block.input);

                    messages.push({ role: 'assistant', content: assistantContent });
                    messages.push({
                        role: 'user',
                        content: [{
                            type: 'tool_result',
                            tool_use_id: block.id,
                            content: toolResult,
                        }],
                    });
                }
            }

            if (!hasToolUse) {
                const finalText = response.content[0]?.text || '';
                messages.push({ role: 'assistant', content: assistantContent });
                console.log(`Agent 完成，共 ${loopCount} 轮`);
                return { response: finalText, messages };
            }
        } catch (error) {
            console.error(`Agent Loop 错误:`, error.message);
            
            // 如果 API 调用失败，返回一个模拟响应
            if (loopCount === 1) {
                const fallbackResponse = generateFallbackResponse(userInput);
                return { response: fallbackResponse, messages };
            }
            
            throw error;
        }
    }

    return { response: '达到最大循环次数', messages };
}

// 生成模拟响应（API 不可用时的降级方案）
function generateFallbackResponse(input) {
    const symbolMatch = input.match(/[A-Z]{1,5}|600519|000858/i);
    const symbol = symbolMatch ? symbolMatch[0].toUpperCase() : '未知';
    
    const prices = { 'AAPL': 168.50, 'NVDA': 520.80, 'TSLA': 245.60, '600519': 1800.00 };
    const names = { 'AAPL': 'Apple Inc.', 'NVDA': 'NVIDIA Corporation', 'TSLA': 'Tesla, Inc.', '600519': '贵州茅台' };
    
    if (prices[symbol]) {
        return `📊 ${symbol}（${names[symbol]}）分析报告\n\n` +
               `💰 行情数据：\n` +
               `• 当前价格：$${prices[symbol].toFixed(2)}\n` +
               `• 涨跌幅：+2.35%\n` +
               `• 成交量：2.5M\n\n` +
               `📈 技术指标：\n` +
               `• RSI：65（中性区间）\n` +
               `• MA_20：$${(prices[symbol] * 0.98).toFixed(2)}\n\n` +
               `💡 注意：当前为模拟数据，API 连接失败。\n` +
               `请检查代理设置或 API 配置。`;
    }
    
    return `抱歉，无法识别股票代码。请使用有效的代码，如：\n• AAPL（苹果）\n• NVDA（英伟达）\n• TSLA（特斯拉）\n• 600519（茅台）`;
}

// HTTP 服务器
const server = http.createServer(async (req, res) => {
    // CORS 头
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://localhost:${PORT}`);

    // 健康检查
    if (url.pathname === '/api/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
            status: 'ok', 
            model: MODEL, 
            base_url: BASE_URL,
            proxy: PROXY_URL
        }));
        return;
    }

    // 聊天接口
    if (url.pathname === '/api/chat' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { message, session_id } = JSON.parse(body);
                console.log(`\n${'='.repeat(50)}`);
                console.log(`收到消息: ${message}`);
                console.log(`会话 ID: ${session_id || 'new'}`);

                const { response, messages } = await agentLoop(message);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    response: response,
                    session_id: session_id || 'session-' + Date.now(),
                }));
            } catch (error) {
                console.error('处理错误:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: error.message }));
            }
        });
        return;
    }

    // 404
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, () => {
    console.log(`\n${'='.repeat(50)}`);
    console.log(`Stock Agent API 运行在 http://localhost:${PORT}/`);
    console.log(`API 健康检查: http://localhost:${PORT}/api/health`);
    console.log(`代理地址: ${PROXY_URL}`);
    console.log(`${'='.repeat(50)}\n`);
});
