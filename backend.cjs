const http = require('http');
const https = require('https');
const { URL } = require('url');
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

// 代理配置
const PROXY_HOST = '127.0.0.1';
const PROXY_PORT = 7897;
const USE_PROXY = true;

console.log(`代理: ${USE_PROXY ? `${PROXY_HOST}:${PROXY_PORT}` : '无'}`);

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

// 工具执行
function executeTool(name, params) {
    console.log(`执行工具: ${name}`, params);
    
    if (name === 'stock_quote') {
        const prices = { 'AAPL': 168.50, 'NVDA': 520.80, 'TSLA': 245.60, '600519': 1800.00 };
        const names = { 'AAPL': 'Apple Inc.', 'NVDA': 'NVIDIA Corporation', 'TSLA': 'Tesla, Inc.', '600519': '贵州茅台' };
        const symbol = (params.symbol || 'AAPL').toUpperCase();
        const price = prices[symbol] || 100;
        
        return JSON.stringify({
            symbol: symbol,
            name: names[symbol] || symbol,
            price: price,
            change: price * 0.02,
            change_pct: 2.0,
            volume: 2500000,
            market_cap: price * 10000000000,
            currency: symbol === '600519' ? 'CNY' : 'USD',
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
    
    return JSON.stringify({ error: 'UNKNOWN_TOOL' });
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

## 免责声明
你是一个分析工具，不是投资顾问。
- 不要给出"买入"、"卖出"、"持有"等具体建议
- 只提供数据分析和客观描述
- 提醒用户投资有风险`;

// 通过代理调用 API
function callClaudeAPIViaProxy(messages) {
    return new Promise((resolve, reject) => {
        const url = new URL(`${BASE_URL}/v1/messages`);
        
        const body = JSON.stringify({
            model: MODEL,
            max_tokens: 4096,
            system: SYSTEM_PROMPT,
            tools: TOOL_DEFINITIONS,
            messages: messages,
        });

        console.log(`调用 Claude API: ${url.href}`);
        console.log(`通过代理: ${PROXY_HOST}:${PROXY_PORT}`);

        // 先连接代理
        const proxyReq = http.request({
            host: PROXY_HOST,
            port: PROXY_PORT,
            method: 'CONNECT',
            path: `${url.hostname}:443`,
        });

        proxyReq.on('connect', (res, socket) => {
            console.log(`代理连接成功: ${res.statusCode}`);
            
            if (res.statusCode !== 200) {
                reject(new Error(`代理连接失败: ${res.statusCode}`));
                return;
            }

            // 通过代理发送 HTTPS 请求
            const tlsOptions = {
                host: url.hostname,
                socket: socket,
                path: url.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': API_KEY,
                    'anthropic-version': '2023-06-01',
                    'Content-Length': Buffer.byteLength(body),
                },
            };

            const httpsReq = https.request(tlsOptions, (httpsRes) => {
                let data = '';
                httpsRes.on('data', chunk => data += chunk);
                httpsRes.on('end', () => {
                    console.log(`API 响应: ${httpsRes.statusCode}`);
                    
                    if (httpsRes.statusCode !== 200) {
                        console.error(`API 错误: ${data}`);
                        reject(new Error(`API 请求失败: ${httpsRes.statusCode}`));
                        return;
                    }

                    try {
                        resolve(JSON.parse(data));
                    } catch (e) {
                        reject(new Error(`解析响应失败: ${e.message}`));
                    }
                });
            });

            httpsReq.on('error', (e) => {
                console.error(`HTTPS 请求错误: ${e.message}`);
                reject(e);
            });

            httpsReq.write(body);
            httpsReq.end();
        });

        proxyReq.on('error', (e) => {
            console.error(`代理连接错误: ${e.message}`);
            reject(e);
        });

        proxyReq.end();
    });
}

// 直接调用 API（不通过代理）
function callClaudeAPIDirect(messages) {
    return new Promise((resolve, reject) => {
        const url = new URL(`${BASE_URL}/v1/messages`);
        
        const body = JSON.stringify({
            model: MODEL,
            max_tokens: 4096,
            system: SYSTEM_PROMPT,
            tools: TOOL_DEFINITIONS,
            messages: messages,
        });

        console.log(`直接调用 Claude API: ${url.href}`);

        const options = {
            hostname: url.hostname,
            port: 443,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': API_KEY,
                'anthropic-version': '2023-06-01',
                'Content-Length': Buffer.byteLength(body),
            },
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                console.log(`API 响应: ${res.statusCode}`);
                
                if (res.statusCode !== 200) {
                    console.error(`API 错误: ${data}`);
                    reject(new Error(`API 请求失败: ${res.statusCode}`));
                    return;
                }

                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(new Error(`解析响应失败: ${e.message}`));
                }
            });
        });

        req.on('error', (e) => {
            console.error(`请求错误: ${e.message}`);
            reject(e);
        });

        req.write(body);
        req.end();
    });
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
            // 尝试通过代理调用，失败则直接调用
            let response;
            try {
                response = await callClaudeAPIViaProxy(messages);
            } catch (proxyError) {
                console.log(`代理调用失败，尝试直接调用...`);
                response = await callClaudeAPIDirect(messages);
            }
            
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
            
            // API 失败时返回模拟响应
            if (loopCount === 1) {
                const fallbackResponse = generateFallbackResponse(userInput);
                return { response: fallbackResponse, messages };
            }
            
            throw error;
        }
    }

    return { response: '达到最大循环次数', messages };
}

// 生成模拟响应
function generateFallbackResponse(input) {
    const prices = { 'AAPL': 168.50, 'NVDA': 520.80, 'TSLA': 245.60, '600519': 1800.00 };
    const names = { 'AAPL': 'Apple Inc.', 'NVDA': 'NVIDIA Corporation', 'TSLA': 'Tesla, Inc.', '600519': '贵州茅台' };
    
    let symbol = '未知';
    for (const [key, value] of Object.entries(names)) {
        if (input.includes(key) || input.includes(value)) {
            symbol = key;
            break;
        }
    }
    if (symbol === '未知' && input.includes('茅台')) symbol = '600519';
    if (symbol === '未知' && input.includes('苹果')) symbol = 'AAPL';
    if (symbol === '未知' && input.includes('英伟达')) symbol = 'NVDA';
    if (symbol === '未知' && input.includes('特斯拉')) symbol = 'TSLA';
    
    if (prices[symbol]) {
        return `[模拟数据 - API 连接失败]\n\n📊 ${symbol}（${names[symbol]}）分析报告\n\n` +
               `💰 行情数据：\n` +
               `• 当前价格：${symbol === '600519' ? '¥' : '$'}${prices[symbol].toFixed(2)}\n` +
               `• 涨跌幅：+2.35%\n` +
               `• 成交量：2.5M\n\n` +
               `📈 技术指标：\n` +
               `• RSI：65（中性区间）\n` +
               `• MA_20：${symbol === '600519' ? '¥' : '$'}${(prices[symbol] * 0.98).toFixed(2)}\n\n` +
               `⚠️ 注意：当前为模拟数据\n` +
               `API 连接失败，请检查代理或网络设置。`;
    }
    
    return `抱歉，无法识别股票代码。请使用有效的代码，如：\n• AAPL（苹果）\n• NVDA（英伟达）\n• TSLA（特斯拉）\n• 600519（茅台）`;
}

// HTTP 服务器
const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://localhost:${PORT}`);

    if (url.pathname === '/api/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
            status: 'ok', 
            model: MODEL, 
            base_url: BASE_URL,
            proxy: USE_PROXY ? `${PROXY_HOST}:${PROXY_PORT}` : 'disabled'
        }));
        return;
    }

    if (url.pathname === '/api/chat' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { message, session_id } = JSON.parse(body);
                console.log(`\n${'='.repeat(50)}`);
                console.log(`收到消息: ${message}`);

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

    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, () => {
    console.log(`\n${'='.repeat(50)}`);
    console.log(`Stock Agent API 运行在 http://localhost:${PORT}/`);
    console.log(`${'='.repeat(50)}\n`);
});
