# -*- coding: utf-8 -*-
"""Agent Loop: core execution loop.

The Agent Loop is the heart of the system:
  user input -> API call -> model returns text or tool_use
  if tool_use: execute tool -> add result to messages -> call API again
  if text: return to user

The model decides which tools to call and when to stop.
This is the key difference from Workflow (where programmer decides).
"""

import anthropic
import json
import logging
import os
from typing import AsyncGenerator

from ..prompts.system import get_system_prompt
from ..models.state import UserContext
from ..tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)


class AgentLoop:
    """Stock Agent core loop.

    Corresponds to oss project's claude-agent.ts chatImpl():
      - Both send messages to Claude API
      - Both parse tool_use blocks and execute tools
      - Both loop until model gives final text response
    """

    def __init__(self, api_key=None, model=None, base_url=None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url or os.environ.get("BASE_URL"),
        )
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.messages = []  # conversation history
        self.user_context = UserContext()

    async def run(self, user_input):
        """Process one user input, return agent response (non-streaming)."""
        self.messages.append({"role": "user", "content": user_input})
        system_prompt = get_system_prompt(self.user_context)

        while True:
            logger.info(f"Agent Loop: API call, messages={len(self.messages)}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=self.messages,
            )

            has_tool_use = False
            assistant_content = []

            for block in response.content:
                assistant_content.append(self._serialize_block(block))
                if block.type == "tool_use":
                    has_tool_use = True
                    logger.info(f"  tool_use: {block.name}")
                    tool_result = execute_tool(block.name, block.input)
                    self.messages.append({"role": "assistant", "content": assistant_content})
                    self.messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": block.id, "content": tool_result}],
                    })

            if not has_tool_use:
                final_text = response.content[0].text if response.content else ""
                self.messages.append({"role": "assistant", "content": assistant_content})
                self._update_context(user_input)
                return final_text

    async def run_sse(self, user_input):
        """Process one user input, yield SSE events for real-time frontend display.

        Same logic as run(), but yields events at each step:
          round_start -> text -> tool_use -> tool_result -> ... -> final_response

        SSE event types (matching Node.js backend.cjs format):
          {"type": "round_start", "round": N}
          {"type": "text", "content": "..."}
          {"type": "tool_use", "name": "...", "input": {...}}
          {"type": "tool_result", "name": "...", "content": "..."}
          {"type": "final_response", "content": "..."}
        """
        self.messages.append({"role": "user", "content": user_input})
        system_prompt = get_system_prompt(self.user_context)

        for round_num in range(1, 11):  # max 10 rounds
            logger.info(f"Agent Loop SSE: round {round_num}, messages={len(self.messages)}")
            yield {"type": "round_start", "round": round_num}

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=self.messages,
            )

            has_tool_use = False
            assistant_content = []

            for block in response.content:
                assistant_content.append(self._serialize_block(block))

                if block.type == "text" and block.text:
                    yield {"type": "text", "content": block.text}

                if block.type == "tool_use":
                    has_tool_use = True
                    yield {"type": "tool_use", "name": block.name, "input": block.input}
                    logger.info(f"  tool_use: {block.name}")
                    tool_result = execute_tool(block.name, block.input)
                    yield {"type": "tool_result", "name": block.name, "content": tool_result}
                    self.messages.append({"role": "assistant", "content": assistant_content})
                    self.messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result", "tool_use_id": block.id, "content": tool_result}],
                    })

            if not has_tool_use:
                final_text = response.content[0].text if response.content else ""
                self.messages.append({"role": "assistant", "content": assistant_content})
                self._update_context(user_input)
                yield {"type": "final_response", "content": final_text}
                return

    def _serialize_block(self, block):
        if block.type == "text":
            return {"type": "text", "text": block.text}
        elif block.type == "tool_use":
            return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
        return {"type": block.type}

    def _update_context(self, user_input):
        # TODO: extract stock symbols from user input
        pass