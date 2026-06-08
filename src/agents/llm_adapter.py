# -*- coding: utf-8 -*-
"""
LLM 适配器 - 封装大模型调用

为什么需要这个？
- 统一 LLM 调用接口
- 支持工具调用（tool_use）
- 处理 API 错误和重试

参考 daily_stock_analysis 的 llm_adapter.py 设计
"""

import json
import os
import httpx
from typing import Dict, Any, List, Optional


class LLMToolAdapter:
    """
    LLM 工具适配器
    
    为什么叫 Adapter？
    - 适配不同的 LLM API（Claude, GPT, etc.）
    - 提供统一的调用接口
    - 处理工具调用的解析
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022",
                 base_url: str = "https://api.anthropic.com",
                 proxy: str = None):
        """
        初始化 LLM 适配器
        
        Args:
            api_key: API 密钥
            model: 模型名称
            base_url: API 基础 URL
            proxy: 代理地址
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.proxy = proxy
    
    def chat(self, system: str, user_message: str = "", 
             tools: List[Dict[str, Any]] = None,
             messages: List[Dict[str, Any]] = None,
             max_tokens: int = 4096) -> Dict[str, Any]:
        """
        调用 LLM chat API
        
        为什么这样设计？
        - 统一的接口，不管用什么模型
        - 支持工具调用
        - 返回标准化的结果
        
        Args:
            system: 系统提示词
            user_message: 用户消息
            tools: 工具定义列表
            max_tokens: 最大 token 数
        
        Returns:
            dict: 包含 content, tool_calls, usage 的结果
        """
        # 构建消息（支持传入历史消息）
        if messages:
            api_messages = messages
        else:
            api_messages = [{"role": "user", "content": user_message}]
        
        # 构建请求体
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": api_messages,
        }
        
        # 如果有工具，添加到请求
        if tools:
            body["tools"] = tools
        
        # 发送请求
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        url = f"{self.base_url}/v1/messages"
        
        try:
            # 使用代理（如果配置了）
            client_kwargs = {}
            if self.proxy:
                client_kwargs["proxy"] = self.proxy
            
            with httpx.Client(**client_kwargs) as client:
                response = client.post(url, json=body, headers=headers, timeout=60)
                response.raise_for_status()
            
            result = response.json()
            
            # 解析结果
            content = ""
            tool_calls = []
            
            for block in result.get("content", []):
                if block["type"] == "text":
                    content += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "name": block["name"],
                        "input": block["input"]
                    })
            
            return {
                "content": content,
                "tool_calls": tool_calls,
                "usage": result.get("usage", {}),
                "stop_reason": result.get("stop_reason")
            }
        
        except Exception as e:
            return {
                "content": "",
                "tool_calls": [],
                "usage": {},
                "error": str(e)
            }
    
    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]], 
                          tool_executor) -> List[Dict[str, Any]]:
        """
        执行工具调用
        
        Args:
            tool_calls: 工具调用列表
            tool_executor: 工具执行函数
        
        Returns:
            list: 工具执行结果列表
        """
        results = []
        for call in tool_calls:
            result = tool_executor(call["name"], call["input"])
            results.append({
                "tool_use_id": call["id"],
                "content": result
            })
        return results
