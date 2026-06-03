"""get_kline 工具：K线数据 + 技术指标。

用户问\"茅台最近一个月怎么样\"，模型调用这个工具。
返回收盘价列表 + MA、RSI、MACD 等技术指标。

为什么单独实现技术指标？
  - yfinance 只提供原始价格数据，不提供技术指标
  - 我们需要自己计算 MA（移动平均）、RSI（相对强弱）、MACD
  - 这些是股票分析的基础工具
"""

import yfinance as yf
import numpy as np
from ..models import KlineResult, AgentError, ERROR_DEFINITIONS
from .quote import _normalize_symbol


def get_kline(
    symbol: str,
    indicators: list[str],
    period: str = '1mo',
    interval: str = '1d',
    market: str = 'US',
) -> KlineResult | AgentError:
    """获取K线数据并计算技术指标。

    Args:
        symbol: 股票代码
        indicators: 要计算的指标列表，如 ['MA', 'RSI', 'MACD']
        period: 时间周期，如 '1mo'（一个月）、'3mo'、'1y'
        interval: K线间隔，如 '1d'（日线）、'1wk'（周线）
        market: 市场

    Returns:
        KlineResult 或 AgentError
    """
    yf_symbol = _normalize_symbol(symbol, market)

    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']

        # 提取日期和收盘价
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
        close = df['Close'].tolist()

        # 计算技术指标
        indicator_results = {}
        for ind in indicators:
            if ind == 'MA':
                indicator_results['MA_5'] = _moving_average(close, 5)
                indicator_results['MA_20'] = _moving_average(close, 20)
            elif ind == 'RSI':
                indicator_results['RSI_14'] = _rsi(close, 14)
            elif ind == 'MACD':
                indicator_results['MACD'] = _macd(close)
            elif ind == 'BB':
                indicator_results['BB'] = _bollinger_bands(close, 20)

        return KlineResult(
            symbol=symbol,
            data_points=len(dates),
            dates=dates,
            close=close,
            indicators=indicator_results,
        )
    except Exception as e:
        if 'No data found' in str(e):
            return ERROR_DEFINITIONS['SYMBOL_NOT_FOUND']
        return ERROR_DEFINITIONS['DATA_UNAVAILABLE']


def _moving_average(data: list[float], window: int) -> list[float | None]:
    """计算移动平均线（MA）。
    
    MA_5 = 最近5天收盘价的平均值
    前4天没有足够数据，返回 None
    """
    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(None)  # 数据不足
        else:
            avg = sum(data[i - window + 1:i + 1]) / window
            result.append(round(avg, 2))
    return result


def _rsi(data: list[float], period: int = 14) -> list[float | None]:
    """计算相对强弱指标（RSI）。
    
    RSI = 100 - 100 / (1 + 平均涨幅 / 平均跌幅)
    RSI > 70 表示超买（可能要跌）
    RSI < 30 表示超卖（可能要涨）
    """
    if len(data) < period + 1:
        return [None] * len(data)

    result = [None] * period  # 前 period 天没有足够数据
    deltas = [data[i] - data[i - 1] for i in range(1, len(data))]

    for i in range(period, len(deltas) + 1):
        window = deltas[i - period:i]
        gains = [d for d in window if d > 0]
        losses = [-d for d in window if d < 0]

        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0.001  # 避免除零

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        result.append(round(rsi, 2))

    return result


def _macd(data: list[float]) -> dict:
    """计算 MACD 指标。
    
    MACD = EMA_12 - EMA_26
    Signal = EMA_9(MACD)
    Histogram = MACD - Signal
    """
    ema_12 = _ema(data, 12)
    ema_26 = _ema(data, 26)

    macd_line = []
    for i in range(len(data)):
        if ema_12[i] is not None and ema_26[i] is not None:
            macd_line.append(round(ema_12[i] - ema_26[i], 4))
        else:
            macd_line.append(None)

    # 计算 Signal 线（MACD 的 9 日 EMA）
    valid_macd = [v for v in macd_line if v is not None]
    signal_line = _ema(valid_macd, 9) if len(valid_macd) >= 9 else [None] * len(valid_macd)

    # 对齐长度
    signal = [None] * (len(macd_line) - len(signal_line)) + signal_line

    return {
        'MACD': macd_line,
        'Signal': signal,
    }


def _ema(data: list[float], period: int) -> list[float | None]:
    """计算指数移动平均（EMA）。
    
    EMA 对最近的数据赋予更高权重。
    EMA_today = price * k + EMA_yesterday * (1 - k)
    k = 2 / (period + 1)
    """
    if len(data) < period:
        return [None] * len(data)

    k = 2 / (period + 1)
    result = [None] * (period - 1)

    # 第一个 EMA 用 SMA 初始化
    sma = sum(data[:period]) / period
    result.append(round(sma, 4))

    # 后续 EMA 递推计算
    for i in range(period, len(data)):
        ema = data[i] * k + result[-1] * (1 - k)
        result.append(round(ema, 4))

    return result


def _bollinger_bands(data: list[float], period: int = 20) -> dict:
    """计算布林带。
    
    中轨 = MA_20
    上轨 = MA_20 + 2 * 标准差
    下轨 = MA_20 - 2 * 标准差
    """
    result = {'upper': [], 'middle': [], 'lower': []}

    for i in range(len(data)):
        if i < period - 1:
            result['upper'].append(None)
            result['middle'].append(None)
            result['lower'].append(None)
        else:
            window = data[i - period + 1:i + 1]
            middle = sum(window) / period
            std = (sum((x - middle) ** 2 for x in window) / period) ** 0.5
            result['middle'].append(round(middle, 2))
            result['upper'].append(round(middle + 2 * std, 2))
            result['lower'].append(round(middle - 2 * std, 2))

    return result
