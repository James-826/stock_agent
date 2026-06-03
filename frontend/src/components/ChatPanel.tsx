import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'

interface ChatPanelProps {
  messages: Array<{role: string, content: string}>
  setMessages: (messages: Array<{role: string, content: string}>) => void
  selectedSymbol: string
}

export default function ChatPanel({ messages, setMessages, selectedSymbol }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = { role: 'user', content: input }
    setMessages([...messages, userMessage])
    setInput('')
    setIsLoading(true)

    // 模拟 API 调用
    setTimeout(() => {
      const botMessage = { 
        role: 'assistant', 
        content: `这是关于 ${selectedSymbol} 的分析结果...\n\n当前价格：$168.50\n涨跌幅：+1.42%\n\n建议：需要综合分析，投资有风险。` 
      }
      setMessages([...messages, userMessage, botMessage])
      setIsLoading(false)
    }, 1500)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden h-[600px] flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b border-slate-200 bg-gradient-to-r from-primary-500 to-primary-600">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-white font-semibold">AI 分析助手</h3>
            <p className="text-primary-100 text-sm">实时股票分析</p>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <Bot className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>开始分析 {selectedSymbol}</p>
            <p className="text-sm mt-1">输入你的问题</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-primary-500 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}
            >
              <div className="flex items-start space-x-2">
                {msg.role === 'assistant' && (
                  <Bot className="w-4 h-4 mt-1 flex-shrink-0 text-primary-500" />
                )}
                <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                {msg.role === 'user' && (
                  <User className="w-4 h-4 mt-1 flex-shrink-0" />
                )}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
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

      {/* 输入框 */}
      <div className="p-4 border-t border-slate-200">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
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
