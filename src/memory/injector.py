# -*- coding: utf-8 -*-
"""
上下文注入模块

Phase 3.3: 为什么需要注入历史记忆？

问题：Agent 每次分析都是"从零开始"
- 用户："NVDA 上次分析是什么时候？"
- Agent："我不知道，让我重新分析"
- 用户："我上次的判断对吗？"
- Agent："我无法回答，我没有历史记录"

解决方案：在分析时，自动查询历史记忆，注入到上下文
- 用户："分析 NVDA"
- Agent 查询历史："上次分析是 6月6日，建议买入，股价从 $210 跌到 $205"
- Agent 结合历史："上次建议买入，但股价跌了，这次我更谨慎"

设计思路：
- 历史记忆是"参考信息"，不是"强制指令"
- 模型可以决定是否采纳历史记忆
- 避免"锚定效应"（过度依赖历史）
"""

from datetime import datetime, timedelta
from typing import Optional
from .history import AnalysisHistory, AnalysisRecord
from .calibration import ConfidenceCalibrator, CalibrationResult


class MemoryInjector:
    """
    记忆注入器
    
    为什么这样设计？
    - 查询历史记录
    - 格式化为模型可读的文本
    - 注入到上下文中
    """
    
    def __init__(self, db_path: str = "analysis_history.db"):
        """
        初始化记忆注入器
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.history = AnalysisHistory(db_path)
        self.calibrator = ConfidenceCalibrator(db_path)
    
    def inject_memory(self, symbol: str, days: int = 30) -> str:
        """
        为指定股票注入历史记忆
        
        Args:
            symbol: 股票代码
            days: 查询最近多少天的历史
        
        Returns:
            str: 格式化的历史记忆文本，可直接注入上下文
        
        流程：
        1. 查询最近的历史分析
        2. 计算校准结果
        3. 格式化为文本
        """
        # 查询最近的历史分析
        recent_analyses = self.history.get_recent_analyses(symbol, limit=5)
        
        # 计算校准结果
        calibration = self.calibrator.calibrate(symbol)
        
        # 格式化为文本
        memory_text = self._format_memory(symbol, recent_analyses, calibration)
        
        return memory_text
    
    def _format_memory(self, symbol: str, analyses: list, calibration: CalibrationResult) -> str:
        """
        将历史记忆格式化为文本
        
        为什么格式化为文本？
        - 模型只能读取文本
        - 文本比 JSON 更容易理解
        - 可以包含人类可读的摘要
        
        Args:
            symbol: 股票代码
            analyses: 历史分析记录列表
            calibration: 校准结果
        
        Returns:
            str: 格式化的历史记忆文本
        """
        lines = []
        lines.append(f"=== {symbol} 历史记忆 ===")
        lines.append("")
        
        # 1. 校准信息
        if calibration.sample_size_sufficient:
            lines.append(f"预测准确率：{calibration.accuracy:.1%}")
            lines.append(f"置信度因子：{calibration.confidence_factor:.2f}")
            lines.append("")
        else:
            lines.append(f"历史数据不足（{calibration.total_predictions} 条），无法校准")
            lines.append("")
        
        # 2. 最近的分析记录
        if analyses:
            lines.append("最近分析记录：")
            for i, record in enumerate(analyses, 1):
                lines.append(f"  {i}. {record.date}: {record.signal} (分数={record.score}) @ ${record.price_at_analysis}")
            lines.append("")
            
            # 3. 最近一次分析的详情
            latest = analyses[0]
            lines.append("最近一次分析详情：")
            lines.append(f"  日期：{latest.date}")
            lines.append(f"  信号：{latest.signal}")
            lines.append(f"  分数：{latest.score}")
            lines.append(f"  趋势：{latest.trend}")
            lines.append(f"  股价：${latest.price_at_analysis}")
            lines.append(f"  摘要：{latest.summary}")
        else:
            lines.append("暂无历史分析记录")
        
        return "\n".join(lines)
    
    def get_context_for_analysis(self, symbol: str) -> dict:
        """
        获取分析时需要的完整上下文
        
        为什么需要这个方法？
        - 一次性获取所有需要的信息
        - 方便 Agent Loop 调用
        - 返回结构化数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            dict: 包含历史记忆、校准结果、建议
        """
        # 查询历史分析
        recent_analyses = self.history.get_recent_analyses(symbol, limit=5)
        
        # 计算校准
        calibration = self.calibrator.calibrate(symbol)
        
        # 生成建议
        suggestion = self._generate_suggestion(recent_analyses, calibration)
        
        return {
            "symbol": symbol,
            "memory_text": self.inject_memory(symbol),
            "calibration": {
                "accuracy": calibration.accuracy,
                "confidence_factor": calibration.confidence_factor,
                "sample_sufficient": calibration.sample_size_sufficient
            },
            "suggestion": suggestion
        }
    
    def _generate_suggestion(self, analyses: list, calibration: CalibrationResult) -> str:
        """
        根据历史记忆生成建议
        
        为什么需要建议？
        - 帮助模型理解历史背景
        - 提供参考，但不强制
        
        Args:
            analyses: 历史分析记录
            calibration: 校准结果
        
        Returns:
            str: 建议文本
        """
        if not analyses:
            return "暂无历史数据，无法提供基于历史的建议"
        
        latest = analyses[0]
        
        # 根据最近的分析生成建议
        if latest.signal in ["strong_buy", "buy"]:
            return f"上次建议买入（{latest.date}），股价从 ${latest.price_at_analysis} 变化。请结合当前情况重新判断。"
        elif latest.signal in ["strong_sell", "sell"]:
            return f"上次建议卖出（{latest.date}），股价从 ${latest.price_at_analysis} 变化。请结合当前情况重新判断。"
        else:
            return f"上次建议观望（{latest.date}），股价 ${latest.price_at_analysis}。请结合当前情况重新判断。"
