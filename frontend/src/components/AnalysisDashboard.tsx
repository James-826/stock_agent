import { useState } from 'react'
import { 
  TrendingUp, TrendingDown, Minus, 
  BarChart3, Newspaper, Brain,
  ChevronDown, ChevronRight,
  Loader2
} from 'lucide-react'

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

interface AnalysisDashboardProps {
  result: AnalysisResult | null
  agentOpinions: AgentOpinion[]
  isLoading: boolean
}

export default function AnalysisDashboard({ result, agentOpinions, isLoading }: AnalysisDashboardProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'strong_buy':
      case 'buy':
        return 'text-emerald-600 bg-emerald-50'
      case 'strong_sell':
      case 'sell':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-amber-600 bg-amber-50'
    }
  }

  const getSignalIcon = (signal: string) => {
    switch (signal) {
      case 'strong_buy':
      case 'buy':
        return <TrendingUp className="w-5 h-5" />
      case 'strong_sell':
      case 'sell':
        return <TrendingDown className="w-5 h-5" />
      default:
        return <Minus className="w-5 h-5" />
    }
  }

  const getSignalText = (signal: string) => {
    switch (signal) {
      case 'strong_buy': return '强烈买入'
      case 'buy': return '买入'
      case 'strong_sell': return '强烈卖出'
      case 'sell': return '卖出'
      default: return '持有'
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-center space-x-3 py-8">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          <span className="text-slate-500">正在分析...</span>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="text-center py-8 text-slate-400">
          <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>输入股票代码开始分析</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* 综合评分 */}
      <div className="p-6 border-b border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">综合分析结果</h3>
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${getSignalColor(result.signal)}`}>
            {getSignalIcon(result.signal)}
            <span className="font-medium">{getSignalText(result.signal)}</span>
          </div>
        </div>
        
        {/* 评分条 */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-slate-500">综合评分</span>
            <span className="text-2xl font-bold text-slate-900">{result.score}/100</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-3">
            <div 
              className={`h-3 rounded-full transition-all duration-500 ${
                result.score >= 70 ? 'bg-emerald-500' : 
                result.score >= 40 ? 'bg-amber-500' : 'bg-red-500'
              }`}
              style={{ width: `${result.score}%` }}
            />
          </div>
        </div>

        {/* 置信度 */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">置信度</span>
          <span className="font-medium text-slate-700">{(result.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* 决策建议 */}
      <div className="p-6 border-b border-slate-200 bg-slate-50">
        <h4 className="text-sm font-medium text-slate-700 mb-2">决策建议</h4>
        <p className="text-sm text-slate-600">{result.reasoning}</p>
        {result.action_advice && (
          <p className="text-sm text-slate-600 mt-2 font-medium">{result.action_advice}</p>
        )}
      </div>

      {/* Agent 详情 */}
      <div className="p-6">
        <h4 className="text-sm font-medium text-slate-700 mb-4">Agent 分析详情</h4>
        <div className="space-y-3">
          {agentOpinions.map((opinion) => (
            <div key={opinion.agent_name} className="border border-slate-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedAgent(expandedAgent === opinion.agent_name ? null : opinion.agent_name)}
                className="w-full flex items-center justify-between p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-1.5 rounded-lg ${getSignalColor(opinion.signal)}`}>
                    {opinion.agent_name === 'technical' ? <BarChart3 className="w-4 h-4" /> :
                     opinion.agent_name === 'intel' ? <Newspaper className="w-4 h-4" /> :
                     <Brain className="w-4 h-4" />}
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-slate-900 capitalize">{opinion.agent_name}</div>
                    <div className="text-xs text-slate-500">{getSignalText(opinion.signal)} • {(opinion.confidence * 100).toFixed(0)}%</div>
                  </div>
                </div>
                {expandedAgent === opinion.agent_name ? 
                  <ChevronDown className="w-4 h-4 text-slate-400" /> :
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                }
              </button>
              
              {expandedAgent === opinion.agent_name && (
                <div className="p-3 bg-slate-50 border-t border-slate-200">
                  <p className="text-sm text-slate-600">{opinion.reasoning}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
