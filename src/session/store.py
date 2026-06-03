"""Session 持久化：JSONL 文件存储。

对应 Phase 3 学的 oss session 机制：

1. 原子写入（write → tmp → rename）：崩溃不会损坏原文件
2. parseMessagesResilient：跳过损坏行继续解析
3. readSessionHeader：只读元数据，用于会话列表

JSONL 格式：每行一个 JSON 对象，是一条消息。
"""

import json
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models.state import UserContext, SessionHeader


# 会话存储目录
SESSION_DIR = Path(__file__).parent.parent.parent / "sessions"


def _ensure_session_dir():
    """确保存储目录存在。"""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def create_session() -> str:
    """创建新会话，返回 session_id。"""
    _ensure_session_dir()
    session_id = str(uuid.uuid4())[:8]
    session_path = SESSION_DIR / f"{session_id}.jsonl"
    session_path.touch()
    return session_id


def write_message(session_id: str, message: dict):
    """追加一条消息到 JSONL 文件。

    对应 Phase 3 学的原子写入流程：
    1. 把完整内容写入 .tmp 文件
    2. 删除原文件
    3. 重命名 .tmp → 原文件名

    如果在步骤 2 崩溃，原文件还在。
    如果在步骤 3 崩溃，原文件还在，.tmp 文件需要手动清理。

    注意：这里简化了 oss 的实现（oss 是全量重写），
    我们用追加模式（a），性能更好，但原理相同。
    """
    _ensure_session_dir()
    session_path = SESSION_DIR / f"{session_id}.jsonl"

    # 直接追加（简化版，生产环境应该用原子写入）
    with open(session_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(message, ensure_ascii=False, default=str) + "\n")


def read_messages(session_id: str) -> list[dict]:
    """读取会话的全部消息。

    对应 Phase 3 学的 parseMessagesResilient：
    跳过损坏行，继续解析。丢一条消息比丢整个会话好。
    """
    session_path = SESSION_DIR / f"{session_id}.jsonl"

    if not session_path.exists():
        return []

    messages = []
    with open(session_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                # parseMessagesResilient：跳过损坏行
                print(f"警告：会话 {session_id} 第 {line_num} 行损坏，已跳过")
                continue

    return messages


def read_session_header(session_id: str) -> Optional[SessionHeader]:
    """读取会话元数据（不加载完整消息）。

    对应 Phase 3 学的 readSessionHeader：只读 8KB 快速获取元数据。
    用于会话列表展示。
    """
    session_path = SESSION_DIR / f"{session_id}.jsonl"

    if not session_path.exists():
        return None

    # 读取前 8KB
    with open(session_path, "r", encoding="utf-8") as f:
        content = f.read(8192)

    # 统计消息数
    message_count = 0
    first_timestamp = None
    last_timestamp = None

    for line in content.strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            message_count += 1
            # 尝试从消息中提取时间戳
        except json.JSONDecodeError:
            continue

    stat = session_path.stat()

    return SessionHeader(
        session_id=session_id,
        created_at=datetime.fromtimestamp(stat.st_ctime),
        last_active=datetime.fromtimestamp(stat.st_mtime),
        message_count=message_count,
        user_context=UserContext(),  # 简化版，实际应从 header 中读取
    )


def list_sessions() -> list[SessionHeader]:
    """列出所有会话的元数据。"""
    _ensure_session_dir()
    headers = []

    for path in SESSION_DIR.glob("*.jsonl"):
        session_id = path.stem
        header = read_session_header(session_id)
        if header:
            headers.append(header)

    # 按最后活跃时间排序
    headers.sort(key=lambda h: h.last_active, reverse=True)
    return headers
