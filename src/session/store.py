# -*- coding: utf-8 -*-
"""Session 持久化：对话历史保存到 JSONL 文件。

Phase 3 学的 Session 机制：
  - JSONL 格式：每行一个 JSON 对象
  - 原子写入：写入临时文件 → 删除原文件 → 重命名
  - 损坏行跳过：解析失败的行不影响其他行
  - Header 快速读取：只读前 8KB，快速展示会话列表

对应 oss 项目的 sessions/jsonl.ts：
  - writeSessionJsonl(): 原子写入
  - readSessionJsonl(): 读取完整会话
  - readSessionHeader(): 只读 header
"""

import json
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


# 会话存储目录
SESSION_DIR = Path('sessions')


def create_session() -> str:
    """创建新会话，返回会话 ID。
    
    会话 ID 是 UUID，用于：
      1. 文件名：sessions/{session_id}.jsonl
      2. 区分不同会话
    """
    session_id = str(uuid.uuid4())
    session_file = SESSION_DIR / f'{session_id}.jsonl'
    
    # 确保目录存在
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    
    # 创建空文件
    session_file.touch()
    
    return session_id


def write_message(session_id: str, message: dict) -> None:
    """写入一条消息到会话文件。
    
    原子写入步骤（对应 Phase 3 学的 4 步）：
      1. 写入临时文件 .tmp
      2. 删除原文件
      3. 重命名临时文件为原文件
    
    为什么这样设计？
      - 如果在写入过程中崩溃，原文件不会损坏
      - 临时文件是新写入的，崩溃了就丢弃
    """
    session_file = SESSION_DIR / f'{session_id}.jsonl'
    tmp_file = SESSION_DIR / f'{session_id}.jsonl.tmp'
    
    # 读取现有内容
    existing_lines = []
    if session_file.exists():
        with open(session_file, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
    
    # 添加新消息
    new_line = json.dumps(message, ensure_ascii=False, default=str) + '\n'
    existing_lines.append(new_line)
    
    # 原子写入
    # Step 1: 写入临时文件
    with open(tmp_file, 'w', encoding='utf-8') as f:
        f.writelines(existing_lines)
    
    # Step 2: 删除原文件
    if session_file.exists():
        session_file.unlink()
    
    # Step 3: 重命名临时文件
    tmp_file.rename(session_file)


def read_session(session_id: str) -> list[dict]:
    """读取完整会话历史。
    
    对应 oss 的 readSessionJsonl()：
      - 逐行解析 JSON
      - 跳过损坏的行（parseMessagesResilient）
    """
    session_file = SESSION_DIR / f'{session_id}.jsonl'
    
    if not session_file.exists():
        return []
    
    messages = []
    with open(session_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                message = json.loads(line)
                messages.append(message)
            except json.JSONDecodeError as e:
                # 跳过损坏的行，继续解析
                print(f'警告：会话 {session_id} 第 {line_num} 行解析失败: {e}')
                continue
    
    return messages


def read_session_header(session_id: str, max_bytes: int = 8192) -> Optional[dict]:
    """读取会话 header（只读前 8KB）。
    
    用途：快速展示会话列表，不需要加载完整历史。
    对应 oss 的 readSessionHeader()。
    """
    session_file = SESSION_DIR / f'{session_id}.jsonl'
    
    if not session_file.exists():
        return None
    
    # 只读前 max_bytes 字节
    with open(session_file, 'r', encoding='utf-8') as f:
        content = f.read(max_bytes)
    
    # 解析第一行作为 header
    lines = content.strip().split('\n')
    if not lines:
        return None
    
    try:
        first_message = json.loads(lines[0])
        return {
            'session_id': session_id,
            'first_message': first_message,
            'created_at': first_message.get('timestamp', ''),
        }
    except json.JSONDecodeError:
        return None


def list_sessions() -> list[dict]:
    """列出所有会话（只读 header）。
    
    用途：展示会话列表，用户选择要恢复哪个会话。
    """
    if not SESSION_DIR.exists():
        return []
    
    sessions = []
    for session_file in SESSION_DIR.glob('*.jsonl'):
        session_id = session_file.stem
        header = read_session_header(session_id)
        if header:
            sessions.append(header)
    
    return sessions
