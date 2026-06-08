# -*- coding: utf-8 -*-
import sys
import os

# Change to project root directory
os.chdir("C:/Users/eddie/Desktop/Agents/Agent学习路线/05-stock-agent")

# Add current directory to path (project root)
sys.path.insert(0, ".")

# Now import using package syntax
from src.tools.registry import execute_tool, TOOL_DEFINITIONS, TOOL_REGISTRY

print("=== Tool Registry Test ===")
print()

# Check registered tools
print("Registered tools:")
for name in TOOL_REGISTRY.keys():
    print(f"  - {name}")

print()
print("Tool definitions for Claude API:")
for tool in TOOL_DEFINITIONS:
    print(f"  - {tool['name']}: {tool['description'][:60]}...")

print()
print("=== Test analyze_trend tool ===")
print("Calling analyze_trend for NVDA...")
result = execute_tool("analyze_trend", {"symbol": "NVDA", "period": "3mo", "market": "US"})

import json
result_dict = json.loads(result)
print()
print(f"Symbol: {result_dict['symbol']}")
print(f"Score: {result_dict['score']}/100")
print(f"Signal: {result_dict['signal']}")
print(f"Trend: {result_dict['trend']}")
print()
print("Summary:")
print(result_dict['summary'])
