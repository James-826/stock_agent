import os, sys
sys.path.insert(0, r'c:\Users\eddie\Desktop\Agents\Agent学习路线\05-stock-agent')
os.chdir(r'c:\Users\eddie\Desktop\Agents\Agent学习路线\05-stock-agent')
from dotenv import load_dotenv
load_dotenv()

from src.agents.orchestrator import AgentOrchestrator
from src.agents.llm_adapter import LLMToolAdapter
from src.tools.registry import TOOL_DEFINITIONS, execute_tool

class R:
    def get_definitions(self): return TOOL_DEFINITIONS
    def execute(self, n, p): return execute_tool(n, p)

api_key = os.environ.get('ANTHROPIC_API_KEY')
model = os.environ.get('CLAUDE_MODEL')
base_url = os.environ.get('BASE_URL')
llm = LLMToolAdapter(api_key=api_key, model=model, base_url=base_url)

from src.agents.technical import TechnicalAgent
from src.agents.intel import IntelAgent
from src.agents.decision import DecisionAgent

orch = AgentOrchestrator(llm, R(), mode='standard')
orch.add_agent(TechnicalAgent(llm, R()))
orch.add_agent(IntelAgent(llm, R()))
orch.add_agent(DecisionAgent(llm, R()))

count = 0
for event in orch.run_stream(stock_code='NVDA', query='test'):
    etype = event.get('type', 'unknown')
    print(f'Event: {etype}')
    if etype == 'agent_complete':
        print(f'  Agent: {event.get("agent_name")}, Signal: {event.get("signal")}')
    count += 1
    if count > 10:
        print('... truncated')
        break
print('Done')
