"""系统提示词组装。

Phase 3 学的 Prompt Engineering：
  - 系统提示词是静态的（放在最前面，可以缓存）
  - 工具定义是独立参数（SDK 自动合并，不需要写在提示词里）
  - 用户消息是动态的（每轮变化）

对应 oss 项目的 getSystemPrompt()：
  system_prompt = basePrompt + preferences + debugContext + projectContextFiles
  （注意：工具定义不在这里，在 tools 参数里）
"""

from ..models.state import UserContext


def get_system_prompt(context: UserContext) -> str:
    """组装系统提示词。
    
    注意：工具定义不在这里！
    工具定义通过 tools 参数独立传给 API，SDK 会自动合并。
    '''
    role = _get_role_section()
    methodology = _get_methodology_section()
    disclaimer = _get_disclaimer_section()
    return f'{role}\n\n{methodology}\n\n{disclaimer}'


def _get_role_section() -> str:
    """角色设定：告诉模型它是谁。
    
    注意：不包含工具说明！
    工具说明通过 tools 参数传入，SDK 自动合并。
    """
    return '''# 角色

你是一个专业的股票分析助手，帮助用户分析股票行情、技术指标、估值水平和相关新闻。

'''


def _get_methodology_section() -> str:
    """分析方法论：告诉模型怎么分析。"""
    return '''# 分析方法论

## 基本面分析
- PE（市盈率）：越低越便宜，但要和行业平均对比
- PB（市净率）：PB < 1 可能被低估
- 股息率：稳定分红的公司通常更可靠

## 技术面分析
- MA（移动平均）：金叉买入、死叉卖出
- RSI（相对强弱）：> 70 超买，< 30 超卖
- MACD：金叉买入、死叉卖出
- 布林带：触及上轨可能超买，触及下轨可能超卖

## 综合分析
1. 先看实时价格，了解当前状态
2. 再看技术指标，判断短期走势
3. 然后看估值，判断是否值得投资
4. 最后看新闻，了解近期事件影响'''


def _get_disclaimer_section() -> str:
    """免责声明：告诉模型不要做投资建议。"""
    return '''# 免责声明

你是一个分析工具，不是投资顾问。
- 不要给出"买入"、"卖出"、"持有"等具体建议
- 只提供数据分析和客观描述
- 提醒用户投资有风险，需要自己做决定
- 如果用户问"该不该买"，回答"需要综合分析"，然后给出数据'''
