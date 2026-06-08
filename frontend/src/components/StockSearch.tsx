import { useState, useRef, useEffect } from 'react'
import { Search, X, Clock, Star } from 'lucide-react'

interface StockSearchProps {
  onSelect: (symbol: string) => void
  selectedSymbol: string
}

// 热门股票
const POPULAR_STOCKS = [
  { symbol: 'NVDA', name: 'NVIDIA' },
  { symbol: 'AAPL', name: 'Apple' },
  { symbol: 'MSFT', name: 'Microsoft' },
  { symbol: 'GOOGL', name: 'Alphabet' },
  { symbol: 'AMZN', name: 'Amazon' },
  { symbol: 'TSLA', name: 'Tesla' },
  { symbol: 'META', name: 'Meta' },
  { symbol: 'AMD', name: 'AMD' },
]

export default function StockSearch({ onSelect, selectedSymbol }: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // 加载最近搜索
  useEffect(() => {
    const saved = localStorage.getItem('recentStockSearches')
    if (saved) {
      setRecentSearches(JSON.parse(saved))
    }
  }, [])

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (symbol: string) => {
    onSelect(symbol)
    setQuery('')
    setIsOpen(false)
    
    // 保存到最近搜索
    const newRecent = [symbol, ...recentSearches.filter(s => s !== symbol)].slice(0, 5)
    setRecentSearches(newRecent)
    localStorage.setItem('recentStockSearches', JSON.stringify(newRecent))
  }

  const filteredStocks = POPULAR_STOCKS.filter(stock =>
    stock.symbol.toLowerCase().includes(query.toLowerCase()) ||
    stock.name.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="flex items-center space-x-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setIsOpen(true)
            }}
            onFocus={() => setIsOpen(true)}
            placeholder="输入股票代码..."
            className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                inputRef.current?.focus()
              }}
              className="absolute right-3 top-1/2 transform -translate-y-1/2"
            >
              <X className="w-4 h-4 text-slate-400 hover:text-slate-600" />
            </button>
          )}
        </div>
        <div className="px-3 py-2 bg-slate-100 rounded-lg">
          <span className="text-sm font-medium text-slate-700">{selectedSymbol}</span>
        </div>
      </div>

      {/* 下拉框 */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-slate-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
          {/* 最近搜索 */}
          {recentSearches.length > 0 && !query && (
            <div className="p-2 border-b border-slate-100">
              <div className="flex items-center space-x-2 px-2 py-1 text-xs text-slate-500">
                <Clock className="w-3 h-3" />
                <span>最近搜索</span>
              </div>
              {recentSearches.map(symbol => (
                <button
                  key={symbol}
                  onClick={() => handleSelect(symbol)}
                  className="w-full flex items-center space-x-3 px-2 py-2 hover:bg-slate-50 rounded-lg transition-colors"
                >
                  <span className="font-medium text-slate-900">{symbol}</span>
                </button>
              ))}
            </div>
          )}

          {/* 热门股票 */}
          <div className="p-2">
            <div className="flex items-center space-x-2 px-2 py-1 text-xs text-slate-500">
              <Star className="w-3 h-3" />
              <span>热门股票</span>
            </div>
            {filteredStocks.map(stock => (
              <button
                key={stock.symbol}
                onClick={() => handleSelect(stock.symbol)}
                className="w-full flex items-center justify-between px-2 py-2 hover:bg-slate-50 rounded-lg transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span className="font-medium text-slate-900">{stock.symbol}</span>
                  <span className="text-sm text-slate-500">{stock.name}</span>
                </div>
                {stock.symbol === selectedSymbol && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
