import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Newspaper } from 'lucide-react'

interface StockDashboardProps {
  symbol: string
  onSymbolChange: (symbol: string) => void
}

// 模拟数据
const mockKlineData = [
  { date: '01-01', price: 150, volume: 1000000 },
  { date: '01-02', price: 152, volume: 1200000 },
  { date: '01-03', price: 148, volume: 900000 },
  { date: '01-04', price: 155, volume: 1500000 },
  { date: '01-05', price: 158, volume: 1800000 },
  { date: '01-06', price: 156, volume: 1100000 },
  { date: '01-07', price: 162, volume: 2000000 },
  { date: '01-08', price: 165, volume: 2200000 },
  { date: '01-09', price: 160, volume: 1600000 },
  { date: '01-10', price: 168, volume: 2500000 },
]

const mockQuote = {
  symbol: 'AAPL',
  name: 'Apple Inc.',
  price: 168.50,
  change: 2.35,
  changePct: 1.42,
  volume: 2500000,
  marketCap: 2800000000000,
}

const mockValuation = {
  pe: 28.5,
  pb: 45.2,
  dividendYield: 0.005,
}

export default function StockDashboard({ symbol, onSymbolChange }: StockDashboardProps) {
  const [activeTab, setActiveTab] = useState<'quote' | 'kline' | 'valuation' | 'news'>('quote')

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* 头部：股票信息 */}
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">{mockQuote.symbol}</h2>
            <p className="text-slate-500">{mockQuote.name}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-slate-900">
              ${mockQuote.price.toFixed(2)}
            </div>
            <div className={`flex items-center justify-end space-x-2 ${mockQuote.change >= 0 ? 'text-success' : 'text-danger'}`}>
              {mockQuote.change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span className="font-medium">
                {mockQuote.change >= 0 ? '+' : ''}{mockQuote.change.toFixed(2)} ({mockQuote.changePct.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>

        {/* 标签页 */}
        <div className="flex space-x-1 bg-slate-100 p-1 rounded-lg">
          {[
            { id: 'quote' as const, label: '行情', icon: DollarSign },
            { id: 'kline' as const, label: 'K线', icon: BarChart3 },
            { id: 'valuation' as const, label: '估值', icon: TrendingUp },
            { id: 'news' as const, label: '新闻', icon: Newspaper },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 flex items-center justify-center space-x-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === id
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 内容区域 */}
      <div className="p-6">
        {activeTab === 'quote' && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-sm text-slate-500 mb-1">成交量</p>
              <p className="text-lg font-semibold text-slate-900">
                {(mockQuote.volume / 1000000).toFixed(2)}M
              </p>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg">
              <p className="text-sm text-slate-500 mb-1">市值</p>
              <p className="text-lg font-semibold text-slate-900">
                ${(mockQuote.marketCap / 1000000000000).toFixed(2)}T
              </p>
            </div>
          </div>
        )}

        {activeTab === 'kline' && (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockKlineData}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'white', 
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }} 
                />
                <Area 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#0ea5e9" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorPrice)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {activeTab === 'valuation' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <span className="text-slate-600">市盈率 (PE)</span>
              <span className="text-lg font-semibold text-slate-900">{mockValuation.pe}</span>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <span className="text-slate-600">市净率 (PB)</span>
              <span className="text-lg font-semibold text-slate-900">{mockValuation.pb}</span>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <span className="text-slate-600">股息率</span>
              <span className="text-lg font-semibold text-slate-900">{(mockValuation.dividendYield * 100).toFixed(2)}%</span>
            </div>
          </div>
        )}

        {activeTab === 'news' && (
          <div className="space-y-4">
            {[
              { title: 'Apple 发布新品', source: 'Reuters', date: '2024-01-10' },
              { title: 'iPhone 销量超预期', source: 'Bloomberg', date: '2024-01-09' },
              { title: 'Apple 股价创新高', source: 'CNBC', date: '2024-01-08' },
            ].map((news, index) => (
              <div key={index} className="p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer">
                <h4 className="font-medium text-slate-900 mb-1">{news.title}</h4>
                <div className="flex items-center space-x-2 text-sm text-slate-500">
                  <span>{news.source}</span>
                  <span>•</span>
                  <span>{news.date}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
