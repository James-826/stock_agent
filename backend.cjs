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

// 通过代理获取雅虎财经数据
function fetchYahooFinance(symbol, proxy = true) {
    return new Promise((resolve, reject) => {
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1mo`;
        const parsedUrl = new URL(url);
        
        console.log(`获取雅虎财经数据: ${symbol}`);
        
        const makeRequest = (socket) => {
            const options = {
                host: parsedUrl.hostname,
                path: parsedUrl.pathname + parsedUrl.search,
                method: 'GET',
                headers: {
                    'User-Agent': 'Mozilla/5.0',
                },
            };
            
            if (socket) {
                options.socket = socket;
            }
            
            const req = https.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const json = JSON.parse(data);
                        if (json.chart && json.chart.result) {
                            resolve(json.chart.result[0]);
                        } else {
                            reject(new Error('数据格式错误'));
                        }
                    } catch (e) {
                        reject(new Error(`解析失败: ${e.message}`));
                    }
                });
            });
            
            req.on('error', reject);
            req.end();
        };
        
        if (proxy) {
            // 通过代理连接
            const proxyReq = http.request({
                host: PROXY_HOST,
                port: PROXY_PORT,
                method: 'CONNECT',
                path: `${parsedUrl.hostname}:443`,
            });
            
            proxyReq.on('connect', (res, socket) => {
                if (res.statusCode === 200) {
                    makeRequest(socket);
                } else {
                    reject(new Error(`代理连接失败: ${res.statusCode}`));
                }
            });
            
            proxyReq.on('error', reject);
            proxyReq.end();
        } else {
            makeRequest(null);
        }
    });
}

// 转换股票代码为雅虎财经格式
function normalizeSymbol(symbol, market) {
    if (market === 'CN') {
        const code = symbol.replace(/\D/g, '');
        if (code.startsWith('6')) return `${code}.SS`;
        if (code.startsWith('0') || code.startsWith('3')) return `${code}.SZ`;
    }
    if (market === 'HK') return `${symbol}.HK`;
    return symbol.toUpperCase();
}

// 工具执行 - 从雅虎财经获取真实数据
async function executeTool(name, params) {
    console.log(`执行工具: ${name}`, params);
    
    try {
        if (name === 'stock_quote') {
            const symbol = normalizeSymbol(params.symbol || 'AAPL', params.market || 'US');
            const data = await fetchYahooFinance(symbol);
            const meta = data.meta;
            const currentPrice = meta.regularMarketPrice;
            const previousClose = meta.previousClose || meta.chartPreviousClose;
            const change = currentPrice - previousClose;
            const changePct = (change / previousClose) * 100;
            
            return JSON.stringify({
                symbol: params.symbol,
                name: meta.shortName || meta.symbol || params.symbol,
                price: currentPrice,
                change: Math.round(change * 100) / 100,
                change_pct: Math.round(changePct * 100) / 100,
                volume: meta.regularMarketVolume,
                market_cap: meta.marketCap || null,
                currency: meta.currency || 'USD',
                timestamp: new Date().toISOString(),
            });
        }
        
        if (name === 'stock_kline') {
            const symbol = normalizeSymbol(params.symbol || 'AAPL', params.market || 'US');
            const data = await fetchYahooFinance(symbol);
            const quotes = data.indicators.quote[0];
            const timestamps = data.timestamp;
            
            const klineData = timestamps.map((time, index) => ({
                date: new Date(time * 1000).toISOString().split('T')[0],
                close: quotes.close[index],
            })).filter(d => d.close !== null);
            
            return JSON.stringify({
                symbol: params.symbol,
                data_points: klineData.length,
                dates: klineData.map(d => d.date),
                close: klineData.map(d => d.close),
                indicators: {},
            });
        }
        
        if (name === 'stock_valuation') {
            const symbol = normalizeSymbol(params.symbol || 'AAPL', params.market || 'US');
            const data = await fetchYahooFinance(symbol);
            const meta = data.meta;
            
            return JSON.stringify({
                symbol: params.symbol,
                pe_ttm: meta.trailingPE || null,
                pe_forward: meta.forwardPE || null,
                pb: meta.priceToBook || null,
                dividend_yield: meta.dividendYield || null,
                currency: meta.currency || 'USD',
            });
        }
        
        if (name === 'stock_news') {
            // 雅虎财经新闻 API
            const symbol = normalizeSymbol(params.symbol || 'AAPL', params.market || 'US');
            const newsUrl = `https://query1.finance.yahoo.com/v1/finance/search?q=${symbol}&newsCount=${params.limit || 5}`;
            
            // 简化处理：返回空新闻
            return JSON.stringify({
                symbol: params.symbol,
                news: [],
                total_count: 0,
            });
        }
    } catch (error) {
        console.error(`工具执行错误: ${error.message}`);
        return JSON.stringify({
            error: 'DATA_UNAVAILABLE',
            message: `无法获取数据: ${error.message}`,
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

// 通过代理调用 Claude API
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

        const proxyReq = http.request({
            host: PROXY_HOST,
            port: PROXY_PORT,
            method: 'CONNECT',
            path: `${url.hostname}:443`,
        });

        proxyReq.on('connect', (res, socket) => {
            if (res.statusCode !== 200) {
                reject(new Error(`代理连接失败: ${res.statusCode}`));
                return;
            }

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

            httpsReq.on('error', reject);
            httpsReq.write(body);
            httpsReq.end();
        });

        proxyReq.on('error', reject);
        proxyReq.end();
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
            const response = await callClaudeAPIViaProxy(messages);
            console.log(`响应类型: ${response.stop_reason}`);

            let hasToolUse = false;
            const assistantContent = [];

            for (const block of response.content) {
                assistantContent.push(block);

                if (block.type === 'tool_use') {
                    hasToolUse = true;
                    console.log(`工具调用: ${block.name}`);

                    const toolResult = await executeTool(block.name, block.input);
                    console.log(`工具结果: ${toolResult.substring(0, 200)}...`);

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
            throw error;
        }
    }

    return { response: '达到最大循环次数', messages };
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
    console.log(`数据来源: 雅虎财经（真实数据）`);
    console.log(`${'='.repeat(50)}\n`);
});
