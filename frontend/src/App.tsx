import { useState, useRef, useEffect } from 'react'
import { 
  Send, Bot, User, Loader2, 
  Menu, X, History, Settings,
  BarChart3, Brain
} from 'lucide-react'
import StockSearch from './components/StockSearch'
import AnalysisDashboard from './components/AnalysisDashboard'
import ThinkingProcess from './components/ThinkingProcess'

const API_BASE = 'http://localhost:8000'

interface Message {
  role: string
  content: string
  type?: string
}

interface AnalysisResult {
  signal: string
  confidence: number
  score: number
  reasoning: string
  technical_summary?: string
  intel_summary?: string
  risk_summary?: string
  action_advice?: string
}

interface AgentOpinion {
  agent_name: string
  signal: string
  confidence: number
  reasoning: string
  raw_data?: Record<string, unknown>
}

interface ThinkingStep {
  round: number
  agent?: string
  tools: Array<{
    name: string
    result?: string
    status?: 'pending' | 'running' | 'completed' | 'error'
  }>
  reasoning?: string
}

export default function App() {
  const [selectedSymbol, setSelectedSymbol] = useState('NVDA')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [agentOpinions, setAgentOpinions] = useState<AgentOpinion[]>([])
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinkingSteps])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)
    setThinkingSteps([])
    setAnalysisResult(null)
    setAgentOpinions([])

    try {
      // 使用新的多 Agent 分析 API
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock_code: selectedSymbol,
          query: input,
          mode: 'standard',
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''
      let finalContent = ''
      const steps: ThinkingStep[] = []
      let currentStep: ThinkingStep | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') continue

          try {
            const event = JSON.parse(dataStr)

            switch (event.type) {
              case 'agent_start':
                // 新 Agent 开始
                currentStep = {
                  round: event.round || steps.length + 1,
                  agent: event.agent,
                  tools: [],
                  reasoning: undefined
                }
                steps.push(currentStep)
                setThinkingSteps([...steps])
                break

              case 'tool_use':
                if (currentStep) {
                  currentStep.tools.push({ 
                    name: event.name || 'unknown',
                    status: 'running'
                  })
                  setThinkingSteps([...steps])
                }
                break

              case 'tool_result':
                if (currentStep && currentStep.tools.length > 0) {
                  const lastTool = currentStep.tools[currentStep.tools.length - 1]
                  lastTool.result = event.content?.substring(0, 200) + '...'
                  lastTool.status = 'completed'
                  setThinkingSteps([...steps])
                }
                break

              case 'agent_complete':
                if (currentStep) {
                  currentStep.reasoning = event.reasoning
                  setThinkingSteps([...steps])
                }
                break

              case 'analysis_result':
                setAnalysisResult(event.result)
                break

              case 'agent_opinion':
                setAgentOpinions(prev => [...prev, event.opinion])
                break

              case 'final_response':
                finalContent = event.content || ''
                break

              case 'session_id':
                setSessionId(event.session_id || null)
                break

              case 'error':
                finalContent = `Error: ${event.message}`
                break
            }
          } catch (e) {
            // Skip malformed JSON
          }
        }
      }

      // Add final response to messages
      if (finalContent) {
        setMessages([...newMessages, { role: 'assistant', content: finalContent }])
      }
    } catch (error) {
      setMessages([...newMessages, {
        role: 'assistant',
        content: `连接错误: ${error instanceof Error ? error.message : '未知错误'}. 请确保 Python 后端已启动。`
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-6 h-6 text-blue-500" />
                <span className="text-xl font-bold text-slate-900">Stock Agent</span>
              </div>
            </div>
            
            <div className="flex-1 max-w-xl mx-8">
              <StockSearch 
                onSelect={setSelectedSymbol}
                selectedSymbol={selectedSymbol}
              />
            </div>

            <div className="flex items-center space-x-2">
              <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
                <History className="w-5 h-5 text-slate-600" />
              </button>
              <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
                <Settings className="w-5 h-5 text-slate-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：分析结果 + 思考过程 */}
          <div className="lg:col-span-2 space-y-6">
            <AnalysisDashboard 
              result={analysisResult}
              agentOpinions={agentOpinions}
              isLoading={isLoading}
            />
            
            {thinkingSteps.length > 0 && (
              <ThinkingProcess 
                steps={thinkingSteps}
                isRunning={isLoading}
              />
            )}
          </div>

          {/* 右侧：聊天面板 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 h-[calc(100vh-180px)] flex flex-col">
              {/* 聊天头部 */}
              <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-blue-500 to-blue-600 rounded-t-xl">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold">AI 分析助手</h3>
                    <p className="text-blue-100 text-sm">多 Agent 协作分析</p>
                  </div>
                </div>
              </div>

              {/* 消息列表 */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center text-slate-400 py-8">
                    <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>开始分析 {selectedSymbol}</p>
                    <p className="text-sm mt-1">输入你的问题</p>
                  </div>
                )}

                {messages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user' 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-slate-100 text-slate-900'
                    }`}>
                      <div className="flex items-start space-x-2">
                        {msg.role === 'assistant' && <Bot className="w-4 h-4 mt-1 flex-shrink-0 text-blue-500" />}
                        <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                        {msg.role === 'user' && <User className="w-4 h-4 mt-1 flex-shrink-0" />}
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && thinkingSteps.length === 0 && (
                  <div className="flex justify-start">
                    <div className="bg-slate-100 rounded-2xl px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                        <span className="text-sm text-slate-500">分析中...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* 输入框 */}
              <div className="p-4 border-t border-slate-200">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder={`询问 ${selectedSymbol} 的情况...`}
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
