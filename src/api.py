# -*- coding: utf-8 -*-
"""FastAPI backend with SSE streaming.

Phase 5: Integrated 3-layer scoring system.
  - trend.py (technical) -> sub-scores for MA/MACD/RSI/Bollinger
  - sentiment.py (sentiment) -> VIX + news + momentum
  - valuation_score.py (valuation) -> PE/PB/ROE/etc.
  - scoring/engine.py (fusion) -> final weighted score

SSE (Server-Sent Events) for real-time streaming:
  - One-way: server -> client
  - Simpler than WebSocket (we only need server push)
  - Auto-reconnect built into browser EventSource
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import os
import asyncio
import re

from .agent.loop import AgentLoop
from .session.store import create_session, write_message, read_session, list_sessions

load_dotenv()

app = FastAPI(title="Stock Agent API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    type: str | None = None


@app.on_event("startup")
async def startup():
    global agent
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("BASE_URL")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    if not api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY")
    agent = AgentLoop(api_key=api_key, model=model, base_url=base_url)
    print(f"Agent initialized: model={model}")


# ============================================================
# Stock name mapping (Chinese -> ticker)
# ============================================================

STOCK_NAME_MAP = {
    "nvidia": "NVDA", "intel": "INTC", "apple": "AAPL", "tesla": "TSLA",
    "microsoft": "MSFT", "google": "GOOGL", "broadcom": "AVGO", "tsmc": "TSM",
    "amd": "AMD", "qualcomm": "QCOM", "netflix": "NFLX", "micron": "MU",
    "meta": "META", "amazon": "AMZN", "nokia": "NOK", "nio": "NIO",
    "alibaba": "BABA", "jd": "JD", "pdd": "PDD", "baidu": "BIDU",
    "byd": "BYDDY", "tencent": "TCEHY",
}


def extract_stock_code(message):
    """Extract stock code from user message (Chinese or English)."""
    stopwords = {"THE","AND","FOR","ARE","BUT","NOT","YOU","ALL","CAN","HER",
                 "WAS","ONE","OUR","OUT","HAS","HOW","MAN","NEW","NOW","OLD",
                 "SEE","WAY","WHO","DID","GET","LET","SAY","SHE","TOO","USE",
                 "TOP","BIG","RED","RUN","SIT","TEN","YES","OK","AI","API"}
    msg_lower = message.lower()
    for name, code in STOCK_NAME_MAP.items():
        if name in msg_lower:
            return code
    patterns = [
        r"分析\s*([A-Za-z][A-Za-z0-9]{0,4})",
        r"查看\s*([A-Za-z][A-Za-z0-9]{0,4})",
        r"([A-Za-z][A-Za-z0-9]{0,4})\s*(?:的情况|股票|怎么样|走势|趋势)",
        r"\b([A-Z]{1,5})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            if code not in stopwords:
                return code
    return None


# ============================================================
# POST /api/chat - SSE streaming chat
# ============================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with SSE streaming.

    Flow:
    1. User sends message -> extract stock code if any
    2. If analysis request -> run quick-analyze first, then LLM
    3. Stream LLM response via SSE
    """
    session_id = request.session_id or create_session()
    write_message(session_id, {"role": "user", "content": request.message})

    stock_code = extract_stock_code(request.message)

    async def event_generator():
        try:
            # Prepend analysis context if stock detected
            context_msg = request.message
            if stock_code:
                try:
                    analysis = await _run_quick_analysis(stock_code)
                    context_msg = (
                        f"[Analysis data for {stock_code}]\n"
                        f"{json.dumps(analysis, ensure_ascii=False, default=str)}\n\n"
                        f"[User question]\n{request.message}"
                    )
                except Exception:
                    pass

            async for event in agent.run_sse(context_msg):
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
                if event.get("type") == "final_response":
                    write_message(session_id, {
                        "role": "assistant",
                        "content": event["content"]
                    })
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ============================================================
# GET /api/quick-analyze/{stock_code} - Fast scoring (no LLM)
# ============================================================

@app.get("/api/quick-analyze/{stock_code}")
async def quick_analyze(stock_code: str):
    """Quick analysis: fetch data + score via 3-layer system. No LLM call.

    This is the core scoring endpoint. It:
    1. Fetches quote (price, change)
    2. Loads K-line data -> technical analysis
    3. Fetches news -> sentiment analysis
    4. Fetches fundamentals -> valuation analysis
    5. Fuses all three -> final score
    """
    result = await _run_quick_analysis(stock_code.upper())
    return {"type": "analysis_result", "result": result}


async def _run_quick_analysis(stock_code: str) -> dict:
    """Internal: run the 3-layer scoring pipeline.

    Returns a dict compatible with the frontend's expected format.
    """
    from .tools.registry import execute_tool
    from .analysis.data_loader import load_kline
    from .analysis.trend import analyze_trend
    from .analysis.sentiment import analyze_sentiment
    from .analysis.valuation_score import analyze_valuation
    from .scoring.engine import fuse_scores

    result = {
        "signal": "hold", "score": 50, "confidence": 0.3,
        "reasoning": "", "action_advice": "", "opinions": [],
        "price": 0, "change_pct": 0, "stock_name": stock_code,
        "stock_code": stock_code,
    }

    # 1. Fetch quote (price, change, name)
    try:
        quote_raw = execute_tool("stock_quote", {"symbol": stock_code, "market": "US"})
        qs = str(quote_raw)
        price_m = re.search(r"price=([\d.]+)", qs)
        change_m = re.search(r"change_pct=([\d.-]+)", qs)
        name_m = re.search(r"name='([^']+)'", qs)
        result["price"] = float(price_m.group(1)) if price_m else 0
        result["change_pct"] = float(change_m.group(1)) if change_m else 0
        result["stock_name"] = name_m.group(1) if name_m else stock_code
    except Exception:
        pass

    # 2. Load K-line + technical analysis
    technical = {"score": 50, "signal": "hold", "trend_state": "ranging",
                 "trend_strength": "weak", "sub_scores": {}, "indicators": {},
                 "volume": {}, "support_resistance": {}}
    try:
        df = load_kline(stock_code, "US", "3mo")
        technical = analyze_trend(stock_code, df)
    except Exception as e:
        print(f"Technical analysis failed: {e}")

    # 3. Fetch news + sentiment analysis
    sentiment = {"score": 50, "signal": "hold", "sub_scores": {},
                 "vix": {}, "news_sentiment": {}, "momentum": {}}
    try:
        news_raw = execute_tool("stock_news", {"symbol": stock_code, "market": "US", "limit": 10})
        # Convert NewsItem objects to dicts for sentiment analyzer
        news_items = []
        if hasattr(news_raw, 'news'):
            for item in news_raw.news:
                news_items.append({"title": item.title, "summary": item.summary, "source": item.source})
        else:
            # Fallback: parse string representation
            qs = str(news_raw)
            for chunk in qs.split("NewsItem(")[1:]:
                title_m = re.search(r"title=['\"](.+?)['\"]", chunk)
                summary_m = re.search(r"summary=['\"](.+?)['\"]", chunk)
                if title_m:
                    news_items.append({"title": title_m.group(1),
                                       "summary": summary_m.group(1) if summary_m else ""})

        df_for_momentum = load_kline(stock_code, "US", "1mo") if technical.get("score", 50) == 50 else None
        try:
            df_for_momentum = load_kline(stock_code, "US", "1mo")
        except Exception:
            df_for_momentum = None

        sentiment = analyze_sentiment(stock_code, df=df_for_momentum, news_items=news_items)
    except Exception as e:
        print(f"Sentiment analysis failed: {e}")

    # 4. Valuation analysis
    valuation = {"score": 50, "signal": "hold", "sub_scores": {}, "data": {}}
    try:
        valuation = analyze_valuation(stock_code)
    except Exception as e:
        print(f"Valuation analysis failed: {e}")

    # 5. Fuse all three layers
    fused = fuse_scores(technical, sentiment, valuation)

    # Build frontend-compatible response
    result["score"] = fused["score"]
    result["signal"] = fused["signal"]
    result["confidence"] = fused["confidence"]
    result["confidence_level"] = fused["confidence_level_cn"]
    result["block_scores"] = fused["block_scores"]
    result["opinions"] = fused["opinions"]
    result["technical_detail"] = technical
    result["sentiment_detail"] = sentiment
    result["valuation_detail"] = valuation
    result["support_resistance"] = technical.get("support_resistance", {})

    # News display (for frontend)
    if sentiment.get("news_sentiment", {}).get("news_count", 0) > 0:
        result["news"] = sentiment["summary"]
    else:
        result["news"] = "No news available"

    # Chinese reasoning
    signal_cn = {"strong_buy": "strong buy", "buy": "buy", "hold": "hold",
                 "watch": "watch", "reduce": "reduce", "sell": "sell"}
    result["reasoning"] = (
        f"{result['stock_name']} ({stock_code}) "
        f"price  ({result['change_pct']:+.1f}%) "
        f"score {fused['score']}/100 signal {fused['signal_cn']}"
    )
    result["action_advice"] = (
        f"Technical {fused['block_scores']['technical']} | "
        f"Sentiment {fused['block_scores']['sentiment']} | "
        f"Valuation {fused['block_scores']['valuation']}"
    )

    return result


# ============================================================
# Session endpoints
# ============================================================

@app.get("/api/sessions")
async def get_sessions():
    return list_sessions()

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    messages = read_session(session_id)
    return {"session_id": session_id, "messages": messages}

@app.post("/api/sessions")
async def create_new_session():
    session_id = create_session()
    return {"session_id": session_id}


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent_initialized": agent is not None}