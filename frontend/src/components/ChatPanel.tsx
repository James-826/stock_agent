import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, ChevronDown, ChevronRight, Wrench } from 'lucide-react'

const API_BASE = 'http://localhost:8000'

interface ChatPanelProps {
  messages: Array<{role: string, content: string, type?: string}>
  setMessages: (messages: Array<{role: string, content: string, type?: string}>) => void
  selectedSymbol: string
}

interface StreamEvent {
  type: string
  content?: string
  name?: string
  input?: Record<string, unknown>
  round?: number
  session_id?: string
  message?: string
}

export default function ChatPanel({ messages, setMessages, selectedSymbol }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [thinkingSteps, setThinkingSteps] = useState<Array<{round: number, tools: Array<{name: string, result?: string}>}>>([])
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinkingSteps])

  const toggleStep = (round: number) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(round)) next.delete(round)
      else next.add(round)
      return next
    })
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setIsLoading(true)
    setThinkingSteps([])

    // Build conversation context for the backend
    const conversationMessages = newMessages
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }))

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
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
      const steps: Array<{round: number, tools: Array<{name: string, result?: string}>}> = []
      let currentStep: {round: number, tools: Array<{name: string, result?: string}>} | null = null

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
            const event: StreamEvent = JSON.parse(dataStr)

            switch (event.type) {
              case 'round_start':
                currentStep = { round: event.round || 1, tools: [] }
                steps.push(currentStep)
                setThinkingSteps([...steps])
                break

              case 'text':
                // Show model thinking in real-time
                break

              case 'tool_use':
                if (currentStep) {
                  currentStep.tools.push({ name: event.name || 'unknown' })
                  setThinkingSteps([...steps])
                }
                break

              case 'tool_result':
                if (currentStep && currentStep.tools.length > 0) {
                  const lastTool = currentStep.tools[currentStep.tools.length - 1]
                  lastTool.result = event.content?.substring(0, 200) + '...'
                  setThinkingSteps([...steps])
                }
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
        content: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}. Make sure the Python backend is running on port 8000.`
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
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden h-[600px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-primary-500 to-primary-600">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-white font-semibold">AI 分析助手</h3>
            <p className="text-primary-100 text-sm">Python Backend + SSE Streaming</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>开始分析 {selectedSymbol}</p>
            <p className="text-sm mt-1">输入你的问题</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === 'user' ? 'bg-primary-500 text-white' : 'bg-slate-100 text-slate-900'
            }`}>
              <div className="flex items-start space-x-2">
                {msg.role === 'assistant' && <Bot className="w-4 h-4 mt-1 flex-shrink-0 text-primary-500" />}
                <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                {msg.role === 'user' && <User className="w-4 h-4 mt-1 flex-shrink-0" />}
              </div>
            </div>
          </div>
        ))}

        {/* Thinking process (real-time) */}
        {isLoading && thinkingSteps.length > 0 && (
          <div className="space-y-2">
            {thinkingSteps.map((step) => (
              <div key={step.round} className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                <button
                  onClick={() => toggleStep(step.round)}
                  className="flex items-center space-x-2 text-xs text-slate-500 hover:text-slate-700 w-full"
                >
                  {expandedSteps.has(step.round)
                    ? <ChevronDown className="w-3 h-3" />
                    : <ChevronRight className="w-3 h-3" />}
                  <span>Round {step.round}</span>
                  {step.tools.length > 0 && (
                    <span className="text-slate-400">
                      - {step.tools.map(t => t.name).join(', ')}
                    </span>
                  )}
                </button>
                {expandedSteps.has(step.round) && step.tools.length > 0 && (
                  <div className="mt-2 space-y-1 pl-5">
                    {step.tools.map((tool, i) => (
                      <div key={i} className="text-xs">
                        <div className="flex items-center space-x-1 text-blue-600">
                          <Wrench className="w-3 h-3" />
                          <span>{tool.name}</span>
                        </div>
                        {tool.result && (
                          <div className="text-slate-400 mt-0.5 pl-4">{tool.result}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {isLoading && thinkingSteps.length === 0 && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-2xl px-4 py-3">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
                <span className="text-sm text-slate-500">分析中...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={`询问 ${selectedSymbol} 的行情...`}
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}