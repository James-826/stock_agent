"""系统提示词组装。

Phase 3 学的 Prompt Engineering：
  - 系统提示词是静态的（放在最前面，可以缓存）
  - 用户消息是动态的（每轮变化）
  
oss 项目的提示词分 4 部分：
  1. basePrompt：角色设定、能力说明
  2. skills：工具列表
  3. preferences：用户偏好
  4. projectContextFiles：项目上下文

我们简化版分 3 部分：
  1. 角色设定 + 能力说明（静态）
  2. 分析方法论（静态）
  3. 免责声明（静态）

为什么静态内容放前面？
  - Claude API 有 Prompt Caching 机制
  - 前缀相同的内容可以缓存，省 token 费用
  - 如果动态内容放前面，每次都要重新计算
"""

from ..models.state import UserContext


def get_system_prompt(context: UserContext) -> str:
    """组装系统提示词。
    
    对应 oss 的 getSystemPrompt()：
      fullPrompt = basePrompt + preferences + debugContext + projectContextFiles
    
    我们简化为：
      system_prompt = role + methodology + disclaimer
    """
    # 第 1 部分：角色设定 + 能力说明
    role = _get_role_section()
    
    # 第 2 部分：分析方法论
    methodology = _get_methodology_section()
    
    # 第 3 部分：免责声明
    disclaimer = _get_disclaimer_section()
    
    # 拼接（静态内容在前，方便缓存）
    return f'{role}\n\n{methodology}\n\n{disclaimer}'


def _get_role_section() -> str:
    """角色设定：告诉模型它是谁。
    
    为什么需要这个？
      - 模型默认是通用助手，不知道自己是股票分析师
      - 明确角色后，模型会用专业术语回答
      - 对应 oss 的 getCraftAssistantPrompt() 里的 role 定义
    """
    return '''# 角色

你是一个专业的股票分析助手，帮助用户分析股票行情、技术指标、估值水平和相关新闻。

## 能力

你可以使用以下工具：
- stock_quote：查询实时价格和涨跌幅
- stock_kline：获取K线数据和技术指标（MA、RSI、MACD、布林带）
- stock_valuation：查询估值指标（PE、PB、股息率）
- stock_news：检索股票相关新闻

## 使用规则

1. 用户问价格相关问题 → 调用 stock_quote
2. 用户问走势/技术分析 → 调用 stock_kline
3. 用户问估值/贵不贵 → 调用 stock_valuation
4. 用户问新闻/原因 → 调用 stock_news
5. 用户问综合分析 → 多次调用工具，综合回答'''


def _get_methodology_section() -> str:
    """分析方法论：告诉模型怎么分析。
    
    为什么需要这个？
      - 模型可能给出泛泛而谈的回答
      - 明确方法论后，模型会按照步骤分析
      - 这就是"Prompt Engineering"的核心：引导模型思考
    """
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
    """免责声明：告诉模型不要做投资建议。
    
    为什么需要这个？
      - 法律风险：不能给具体投资建议
      - 明确边界：模型是分析工具，不是投资顾问
      - 对应 PRD 里的"分析助手，非投资顾问"
    '''
    return '''# 免责声明

你是一个分析工具，不是投资顾问。
- 不要给出"买入"、"卖出"、"持有"等具体建议
- 只提供数据分析和客观描述
- 提醒用户投资有风险，需要自己做决定
- 如果用户问"该不该买"，回答"需要综合分析"，然后给出数据'''
