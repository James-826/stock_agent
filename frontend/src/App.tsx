import { useState } from 'react'
import ChatPanel from './components/ChatPanel'
import StockDashboard from './components/StockDashboard'
import Header from './components/Header'

function App() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('AAPL')
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Header />
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧：股票仪表盘 */}
          <div className="lg:col-span-2">
            <StockDashboard 
              symbol={selectedSymbol} 
              onSymbolChange={setSelectedSymbol}
            />
          </div>
          
          {/* 右侧：聊天面板 */}
          <div className="lg:col-span-1">
            <ChatPanel 
              messages={messages}
              setMessages={setMessages}
              selectedSymbol={selectedSymbol}
            />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
