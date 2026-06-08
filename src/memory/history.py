# -*- coding: utf-8 -*-
"""Analysis History Storage

Phase 3.1: Why store analysis history?

Problem: Agent makes the same analysis repeatedly
- User asks "Analyze NVDA" today
- User asks "Analyze NVDA" tomorrow
- Agent doesn't remember yesterday's analysis

Solution: Store analysis results in SQLite
- Each analysis: stock, date, score, signal, price
- Query history: "What did I analyze yesterday?"
- Calibration: Compare past predictions with actual outcomes

Why SQLite instead of JSON?
- Concurrent access (multiple sessions)
- Complex queries (JOIN, GROUP BY, aggregate)
- Better for large datasets
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
import json


@dataclass
class AnalysisRecord:
    """Analysis record stored in database.
    
    Why dataclass?
    - Clear structure
    - Easy to serialize/deserialize
    - Type hints for IDE
    """
    id: Optional[int] = None
    symbol: str = ""
    date: str = ""
    score: int = 0
    signal: str = ""
    trend: str = ""
    price_at_analysis: float = 0.0
    indicators: dict = None
    summary: str = ""
    created_at: str = ""


class AnalysisHistory:
    """SQLite storage for analysis history.
    
    Why this design?
    - Single table for simplicity
    - JSON field for flexible indicator storage
    - Auto-increment ID for unique records
    """
    
    def __init__(self, db_path: str = "analysis_history.db"):
        """Initialize database connection.
        
        Args:
            db_path: SQLite database file path
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    signal TEXT NOT NULL,
                    trend TEXT NOT NULL,
                    price_at_analysis REAL NOT NULL,
                    indicators TEXT,
                    summary TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_date 
                ON analysis_history(symbol, date)
            """)
    
    def save_analysis(self, record: AnalysisRecord) -> int:
        """Save analysis record to database.
        
        Args:
            record: AnalysisRecord to save
        
        Returns:
            ID of saved record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO analysis_history 
                (symbol, date, score, signal, trend, price_at_analysis, 
                 indicators, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.symbol,
                record.date,
                record.score,
                record.signal,
                record.trend,
                record.price_at_analysis,
                json.dumps(record.indicators, ensure_ascii=False),
                record.summary,
                record.created_at or datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def get_recent_analyses(self, symbol: str, limit: int = 10) -> List[AnalysisRecord]:
        """Get recent analyses for a stock.
        
        Args:
            symbol: stock code
            limit: number of records to return
        
        Returns:
            List of AnalysisRecord
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM analysis_history 
                WHERE symbol = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (symbol, limit)).fetchall()
            
            return [self._row_to_record(row) for row in rows]
    
    def get_analysis_by_date(self, symbol: str, date: str) -> Optional[AnalysisRecord]:
        """Get analysis for a specific date.
        
        Args:
            symbol: stock code
            date: date string (YYYY-MM-DD)
        
        Returns:
            AnalysisRecord or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM analysis_history 
                WHERE symbol = ? AND date = ?
            """, (symbol, date)).fetchone()
            
            return self._row_to_record(row) if row else None
    
    def _row_to_record(self, row) -> AnalysisRecord:
        """Convert database row to AnalysisRecord."""
        return AnalysisRecord(
            id=row["id"],
            symbol=row["symbol"],
            date=row["date"],
            score=row["score"],
            signal=row["signal"],
            trend=row["trend"],
            price_at_analysis=row["price_at_analysis"],
            indicators=json.loads(row["indicators"]) if row["indicators"] else {},
            summary=row["summary"],
            created_at=row["created_at"]
        )
    
    def get_accuracy_stats(self, symbol: str) -> dict:
        """Calculate prediction accuracy statistics.
        
        Why accuracy stats?
        - Calibration: Is our scoring system reliable?
        - Improvement: Identify which signals work best
        
        Returns:
            dict with accuracy metrics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all analyses with their outcomes
            rows = conn.execute("""
                SELECT * FROM analysis_history 
                WHERE symbol = ? 
                ORDER BY date ASC
            """, (symbol,)).fetchall()
            
            if len(rows) < 2:
                return {"total": len(rows), "accuracy": None}
            
            correct = 0
            total = 0
            
            for i in range(1, len(rows)):
                prev = rows[i-1]
                curr = rows[i]
                
                # Did the prediction match reality?
                prev_signal = prev["signal"]
                price_change = curr["price_at_analysis"] - prev["price_at_analysis"]
                
                if prev_signal in ["strong_buy", "buy"] and price_change > 0:
                    correct += 1
                elif prev_signal in ["strong_sell", "sell"] and price_change < 0:
                    correct += 1
                elif prev_signal == "neutral":
                    correct += 1  # Neutral is always "correct"
                
                total += 1
            
            return {
                "total": total,
                "correct": correct,
                "accuracy": round(correct / total * 100, 2) if total > 0 else 0
            }
