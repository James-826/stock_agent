"""Agent Loop：核心运行循环。

对应 Phase 2 学的 Agent Loop 机制：
    用户输入
        ↓
    API call: system + tools + messages → Claude
        ↓
    Claude 返回: text（最终回答）或 tool_use（要调工具）
        ↓
    如果 tool_use:
        执行工具 → 把结果加入 messages → 再次 API call
        ↓
    如果 text:
        返回给用户

这个循环是 Agent 的核心。控制权在模型手里——模型决定
"要调几个工具、调哪些工具"，
程序员不写死流程（这正是 Agent 和 Workflow 的区别）。

对应 oss 项目的 claude-agent.ts 的 chatImpl()。
"""

import anthropic
import json
import logging
import os
from typing import AsyncGenerator

from ..prompts.system import get_system_prompt
from ..models.state import UserContext
from .registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


class AgentLoop:
    """Stock Agent 的核心循环。
    
    和 oss 的 ClaudeAgent 对应：
      - oss 用 Anthropic SDK 的 query() 方法启动循环
      - 我们用 anthropic.Anthropic 的 messages.create() 方法
      - 本质一样：发消息给模型，处理返回，循环直到模型给出最终回答
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        # 支持自定义 API 地址（第三方代理）
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get('ANTHROPIC_API_KEY'),
            base_url=base_url or os.environ.get('BASE_URL'),
        )
        self.model = model or os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-6')
        self.messages: list[dict] = []  # 对话历史
        self.user_context = UserContext()

    async def run(self, user_input: str) -> str:
        """处理一次用户输入，返回 Agent 的回答。
        
        这就是 Agent Loop 的完整实现：
        
        1. 把用户输入加入 messages
        2. 组装 system prompt + tools + messages
        3. 调用 Claude API
        4. 如果返回 tool_use → 执行工具 → 结果加入 messages → 回到 3
        5. 如果返回 text → 返回给用户
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            Agent 的文字回答
        """
        # Step 1: 加入用户消息
        self.messages.append({'role': 'user', 'content': user_input})

        # Step 2: 组装 system prompt
        system_prompt = get_system_prompt(self.user_context)

        # Step 3-5: Agent Loop
        while True:
            logger.info(f'Agent Loop: 发送 API call，messages 长度 = {len(self.messages)}')

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=self.messages,
            )

            # 检查模型的响应
            # response.content 是一个列表，可能包含 text 和 tool_use 两种 block
            has_tool_use = False
            assistant_content = []

            for block in response.content:
                assistant_content.append(self._serialize_block(block))

                if block.type == 'tool_use':
                    has_tool_use = True
                    # Step 4: 执行工具
                    logger.info(f'  工具调用: {block.name}({json.dumps(block.input, ensure_ascii=False)})')

                    tool_result = execute_tool(block.name, block.input)

                    logger.info(f'  工具结果: {tool_result[:200]}...')

                    # 把 assistant 的 tool_use 消息加入历史
                    # 注意：需要先加 assistant 消息，再加 tool_result 消息
                    self.messages.append({'role': 'assistant', 'content': assistant_content})
                    # tool_result 作为 user 消息（Anthropic API 的约定）
                    self.messages.append({
                        'role': 'user',
                        'content': [{
                            'type': 'tool_result',
                            'tool_use_id': block.id,
                            'content': tool_result,
                        }],
                    })

            if not has_tool_use:
                # Step 5: 模型给出了最终文字回答
                final_text = response.content[0].text if response.content else ''

                # 把 assistant 的最终回答加入历史
                self.messages.append({'role': 'assistant', 'content': assistant_content})

                # 更新用户上下文
                self._update_context(user_input)

                return final_text

            # has_tool_use = True，继续循环（模型可能还要调更多工具）

    def _serialize_block(self, block) -> dict:
        """把 SDK 的 block 对象序列化为 dict（用于 messages 历史）。"""
        if block.type == 'text':
            return {'type': 'text', 'text': block.text}
        elif block.type == 'tool_use':
            return {'type': 'tool_use', 'id': block.id, 'name': block.name, 'input': block.input}
        return {'type': block.type}

    def _update_context(self, user_input: str):
        """更新用户上下文（跨轮次保持的信息）。
        
        简单策略：从用户输入中提取股票代码
        实际生产中会用 NER 或正则，这里简化处理
        """
        # TODO: 后续实现
        pass
