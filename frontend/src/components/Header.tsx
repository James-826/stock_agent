import { TrendingUp, Activity, BarChart3 } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white border-b border-slate-200 shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Stock Agent</h1>
              <p className="text-sm text-slate-500">AI 股票分析助手</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm text-slate-600">
              <Activity className="w-4 h-4 text-success" />
              <span>实时数据</span>
            </div>
            <div className="flex items-center space-x-2 text-sm text-slate-600">
              <BarChart3 className="w-4 h-4 text-primary-500" />
              <span>技术分析</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
