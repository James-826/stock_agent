# -*- coding: utf-8 -*-
"""Stock Agent 入口文件。

运行方式：
    cd 05-stock-agent
    python -m src.main

需要环境变量：
    ANTHROPIC_API_KEY=sk-ant-...
"""

import asyncio
import sys
import os

from .agent.loop import AgentLoop
from .session.store import create_session, write_message


async def main():
    """交互式 CLI。"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print('错误：请设置环境变量 ANTHROPIC_API_KEY')
        print('  export ANTHROPIC_API_KEY=sk-ant-...')
        sys.exit(1)

    # 创建 Agent 和 Session
    agent = AgentLoop(api_key=api_key)
    session_id = create_session()

    print('=' * 60)
    print('  Stock Analysis Agent')
    print('  输入股票相关问题，输入 quit 退出')
    print('=' * 60)
    print(f'  会话 ID: {session_id}')
    print()

    while True:
        try:
            user_input = input('你: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n再见！')
            break

        if not user_input:
            continue
        if user_input.lower() in ('quit', 'exit', 'q'):
            print('再见！')
            break

        # 记录用户消息
        write_message(session_id, {'role': 'user', 'content': user_input})

        try:
            # Agent Loop 处理
            response = await agent.run(user_input)
            print(f'\nAgent: {response}\n')

            # 记录 Agent 回答
            write_message(session_id, {'role': 'assistant', 'content': response})

        except Exception as e:
            error_msg = f'处理出错: {e}'
            print(f'\n{error_msg}\n')
            write_message(session_id, {'role': 'system', 'content': error_msg})


if __name__ == '__main__':
    asyncio.run(main())
