const http = require('http');
const https = require('https');
const { URL } = require('url');
const fs = require('fs');
const path = require('path');

// 加载 .env
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
    fs.readFileSync(envPath, 'utf-8').split('\n').forEach(line => {
        const [key, ...val] = line.split('=');
        if (key && !key.startsWith('#')) process.env[key.trim()] = val.join('=').trim();
    });
}

const PORT = process.env.PORT || 8000;
const API_KEY = process.env.ANTHROPIC_API_KEY;
const BASE_URL = process.env.BASE_URL || 'https://api.anthropic.com';
const MODEL = process.env.CLAUDE_MODEL || 'claude-sonnet-4-6';
const PROXY_HOST = '127.0.0.1';
const PROXY_PORT = 7897;

if (!API_KEY) { console.error('错误：请设置 ANTHROPIC_API_KEY'); process.exit(1); }

console.log(`Stock Agent API 启动中...`);
console.log(`模型: ${MODEL}`);

// ========== Session 存储 ==========
const SESSION_DIR = path.join(__dirname, 'sessions');
if (!fs.existsSync(SESSION_DIR)) fs.mkdirSync(SESSION_DIR, { recursive: true });
const sessions = new Map();

function loadSessions() {
    fs.readdirSync(SESSION_DIR).filter(f => f.endsWith('.json')).forEach(file => {
        try {
            const id = file.replace('.json', '');
            sessions.set(id, JSON.parse(fs.readFileSync(path.join(SESSION_DIR, file), 'utf-8')));
        } catch (e) {}
    });
    console.log(`加载了 ${sessions.size} 个 sessions`);
}

function saveSession(id, data) {
    fs.writeFileSync(path.join(SESSION_DIR, `${id}.json`), JSON.stringify(data, null, 2));
}

function createSession() {
    const id = 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const data = { id, messages: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString(), title: '新会话' };
    sessions.set(id, data);
    saveSession(id, data);
    return data;
}

function getSession(id) { return sessions.get(id); }
function updateSession(id, updates) {
    const s = sessions.get(id);
    if (!s) return null;
    Object.assign(s, updates, { updated_at: new Date().toISOString() });
    saveSession(id, s);
    return s;
}

loadSessions();

// ========== 工具定义 ==========
const TOOL_DEFINITIONS = [
    {
        name: 'stock_quote',
        description: '查询股票实时价格和涨跌幅',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'], description: '市场' },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_kline',
        description: '获取K线数据和技术指标',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                period: { type: 'string', enum: ['1mo', '3mo', '6mo', '1y'] },
                market: { type: 'string', enum: ['US', 'CN', 'HK'] },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_valuation',
        description: '查询估值指标（PE、PB、股息率）',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'] },
            },
            required: ['symbol'],
        },
    },
    {
        name: 'stock_news',
        description: '检索股票相关新闻',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: '股票代码' },
                limit: { type: 'integer' },
                market: { type: 'string', enum: ['US', 'CN', 'HK'] },
            },
            required: ['symbol'],
        },
    },
];

// ========== 雅虎财经 ==========
function fetchYahooFinance(symbol) {
    return new Promise((resolve, reject) => {
        const url = new URL(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1mo`);
        const makeRequest = (socket) => {
            const options = { host: url.hostname, path: url.pathname + url.search, method: 'GET', headers: { 'User-Agent': 'Mozilla/5.0' } };
            if (socket) options.socket = socket;
            https.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const json = JSON.parse(data);
                        json.chart?.result ? resolve(json.chart.result[0]) : reject(new Error('数据格式错误'));
                    } catch (e) { reject(e); }
                });
            }).on('error', reject).end();
        };
        const proxyReq = http.request({ host: PROXY_HOST, port: PROXY_PORT, method: 'CONNECT', path: `${url.hostname}:443` });
        proxyReq.on('connect', (res, socket) => res.statusCode === 200 ? makeRequest(socket) : reject(new Error('代理失败')));
        proxyReq.on('error', reject);
        proxyReq.end();
    });
}

function normalizeSymbol(symbol, market) {
    if (market === 'CN') {
        const code = symbol.replace(/\D/g, '');
        return code.startsWith('6') ? `${code}.SS` : `${code}.SZ`;
    }
    if (market === 'HK') return `${symbol}.HK`;
    return symbol.toUpperCase();
}

async function executeTool(name, params) {
    console.log(`执行工具: ${name}`, params);
    try {
        if (name === 'stock_quote') {
            const data = await fetchYahooFinance(normalizeSymbol(params.symbol, params.market));
            const meta = data.meta;
            const price = meta.regularMarketPrice;
            const prev = meta.previousClose || meta.chartPreviousClose;
            return JSON.stringify({
                symbol: params.symbol, name: meta.shortName || params.symbol,
                price, change: Math.round((price - prev) * 100) / 100,
                change_pct: Math.round(((price - prev) / prev) * 10000) / 100,
                volume: meta.regularMarketVolume, market_cap: meta.marketCap,
                currency: meta.currency, timestamp: new Date().toISOString(),
            });
        }
        if (name === 'stock_kline') {
            const data = await fetchYahooFinance(normalizeSymbol(params.symbol, params.market));
            const quotes = data.indicators.quote[0];
            const kline = data.timestamp.map((t, i) => ({ date: new Date(t * 1000).toISOString().split('T')[0], close: quotes.close[i] })).filter(d => d.close);
            return JSON.stringify({ symbol: params.symbol, data_points: kline.length, dates: kline.map(d => d.date), close: kline.map(d => d.close) });
        }
        if (name === 'stock_valuation') {
            const data = await fetchYahooFinance(normalizeSymbol(params.symbol, params.market));
            const m = data.meta;
            return JSON.stringify({ symbol: params.symbol, pe_ttm: m.trailingPE, pe_forward: m.forwardPE, pb: m.priceToBook, dividend_yield: m.dividendYield, currency: m.currency });
        }
        if (name === 'stock_news') return JSON.stringify({ symbol: params.symbol, news: [], total_count: 0 });
    } catch (e) {
        return JSON.stringify({ error: 'DATA_UNAVAILABLE', message: e.message });
    }
    return JSON.stringify({ error: 'UNKNOWN_TOOL' });
}

// ========== 系统提示词 ==========
const SYSTEM_PROMPT = `你是一个专业的股票分析助手。记住用户之前提到的股票，如果用户使用代词（它、这家），根据上下文推断。

你可以使用工具：stock_quote（实时价格）、stock_kline（K线）、stock_valuation（估值）、stock_news（新闻）

不要给出投资建议，只提供数据分析。提醒用户投资有风险。`;

// ========== Claude API ==========
function callClaudeAPI(messages) {
    return new Promise((resolve, reject) => {
        const url = new URL(`${BASE_URL}/v1/messages`);
        const body = JSON.stringify({ model: MODEL, max_tokens: 4096, system: SYSTEM_PROMPT, tools: TOOL_DEFINITIONS, messages });
        console.log(`调用 API: ${url.href}, 消息数: ${messages.length}`);
        const proxyReq = http.request({ host: PROXY_HOST, port: PROXY_PORT, method: 'CONNECT', path: `${url.hostname}:443` });
        proxyReq.on('connect', (res, socket) => {
            if (res.statusCode !== 200) return reject(new Error('代理失败'));
            const req = https.request({
                host: url.hostname, socket, path: url.pathname, method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY, 'anthropic-version': '2023-06-01', 'Content-Length': Buffer.byteLength(body) },
            }, (apiRes) => {
                let data = '';
                apiRes.on('data', chunk => data += chunk);
                apiRes.on('end', () => {
                    console.log(`API 响应: ${apiRes.statusCode}`);
                    apiRes.statusCode === 200 ? resolve(JSON.parse(data)) : reject(new Error(`API 错误: ${apiRes.statusCode}`));
                });
            });
            req.on('error', reject);
            req.write(body);
            req.end();
        });
        proxyReq.on('error', reject);
        proxyReq.end();
    });
}

// ========== SSE Agent Loop ==========
async function agentLoopSSE(userInput, sessionId, sendEvent) {
    let session = getSession(sessionId);
    if (!session) session = createSession();
    
    session.messages.push({ role: 'user', content: userInput });
    if (session.messages.length === 1) session.title = userInput.substring(0, 50);

    // user_message 不再通过 SSE 发送，前端本地已添加

    for (let i = 0; i < 10; i++) {
        console.log(`\nAgent Loop 第 ${i + 1} 轮`);
        sendEvent('round_start', { round: i + 1 });
        
        const response = await callClaudeAPI(session.messages);
        let hasToolUse = false;
        const assistantContent = [];

        // 先发送所有 text 块作为中间事件（让前端实时显示模型思考）
        for (const block of response.content) {
            if (block.type === 'text' && block.text) {
                sendEvent('text', { content: block.text });
            }
        }

        for (const block of response.content) {
            assistantContent.push(block);

            if (block.type === 'tool_use') {
                hasToolUse = true;
                sendEvent('tool_use', { name: block.name, input: block.input });

                const result = await executeTool(block.name, block.input);
                sendEvent('tool_result', { name: block.name, content: result });

                // 用 slice() 避免引用累积问题
                session.messages.push({ role: 'assistant', content: assistantContent.slice() });
                session.messages.push({ role: 'user', content: [{ type: 'tool_result', tool_use_id: block.id, content: result }] });
            }
        }

        if (!hasToolUse) {
            const finalText = response.content.filter(b => b.type === 'text').map(b => b.text).join('');
            session.messages.push({ role: 'assistant', content: assistantContent });
            updateSession(session.id, session);
            sendEvent('final_response', { content: finalText, session_id: session.id });
            return;
        }
    }
}

// ========== HTTP 服务器 ==========
const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

    const url = new URL(req.url, `http://localhost:${PORT}`);

    if (url.pathname === '/api/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', model: MODEL, sessions: sessions.size }));
        return;
    }

    if (url.pathname === '/api/sessions' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(Array.from(sessions.values()).map(s => ({ id: s.id, title: s.title, created_at: s.created_at, updated_at: s.updated_at, message_count: s.messages.length }))));
        return;
    }

    if (url.pathname === '/api/sessions' && req.method === 'POST') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(createSession()));
        return;
    }

    if (url.pathname.startsWith('/api/sessions/') && req.method === 'GET') {
        const session = getSession(url.pathname.split('/').pop());
        session ? (res.writeHead(200, { 'Content-Type': 'application/json' }), res.end(JSON.stringify(session))) : (res.writeHead(404), res.end('Not found'));
        return;
    }

    // SSE 聊天接口
    if (url.pathname === '/api/chat' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { message, session_id } = JSON.parse(body);
                console.log(`\n${'='.repeat(50)}\n收到: ${message}`);

                // 设置 SSE
                res.writeHead(200, {
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                });

                const sendEvent = (type, data) => {
                    res.write(`data: ${JSON.stringify({ type, ...data })}\n\n`);
                    console.log(`SSE: ${type}`, data.name || '');
                };

                await agentLoopSSE(message, session_id || createSession().id, sendEvent);
                
                res.write('data: [DONE]\n\n');
                res.end();
            } catch (error) {
                console.error('错误:', error);
                res.write(`data: ${JSON.stringify({ type: 'error', message: error.message })}\n\n`);
                res.end();
            }
        });
        return;
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(PORT, () => {
    console.log(`\n${'='.repeat(50)}\nStock Agent API: http://localhost:${PORT}/\n${'='.repeat(50)}\n`);
});
