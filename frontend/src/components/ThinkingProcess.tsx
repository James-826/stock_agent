import { useState } from 'react'
import { 
  ChevronDown, ChevronRight, 
  Loader2, CheckCircle, AlertCircle,
  Wrench, Brain
} from 'lucide-react'

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

interface ThinkingProcessProps {
  steps: ThinkingStep[]
  isRunning: boolean
}

export default function ThinkingProcess({ steps, isRunning }: ThinkingProcessProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([1]))
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())

  const toggleStep = (round: number) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(round)) next.delete(round)
      else next.add(round)
      return next
    })
  }

  const toggleTool = (key: string) => {
    setExpandedTools(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const getStepStatus = (step: ThinkingStep) => {
    if (step.tools.some(t => t.status === 'error')) return 'error'
    if (step.tools.every(t => t.status === 'completed')) return 'completed'
    if (step.tools.some(t => t.status === 'running')) return 'running'
    return 'pending'
  }

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-emerald-500" />
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <div className="w-4 h-4 rounded-full border-2 border-slate-300" />
    }
  }

  const getAgentLabel = (agent?: string) => {
    switch (agent) {
      case 'technical': return '技术面分析'
      case 'intel': return '消息面分析'
      case 'decision': return '综合决策'
      default: return `第 ${steps.findIndex(s => s === arguments[0]) + 1} 步`
    }
  }

  if (steps.length === 0 && !isRunning) {
    return null
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 bg-slate-100">
        <div className="flex items-center space-x-2">
          <Brain className="w-4 h-4 text-slate-600" />
          <span className="text-sm font-medium text-slate-700">思考过程</span>
          {isRunning && (
            <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
          )}
        </div>
      </div>

      <div className="p-3 space-y-2">
        {steps.map((step) => {
          const status = getStepStatus(step)
          const isExpanded = expandedSteps.has(step.round)

          return (
            <div key={step.round} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
              <button
                onClick={() => toggleStep(step.round)}
                className="w-full flex items-center justify-between p-3 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  {getStepIcon(status)}
                  <div className="text-left">
                    <div className="text-sm font-medium text-slate-900">
                      {step.agent ? getAgentLabel(step.agent) : `Round ${step.round}`}
                    </div>
                    <div className="text-xs text-slate-500">
                      {step.tools.length} 个工具调用
                    </div>
                  </div>
                </div>
                {isExpanded ? 
                  <ChevronDown className="w-4 h-4 text-slate-400" /> :
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                }
              </button>

              {isExpanded && (
                <div className="p-3 bg-slate-50 border-t border-slate-200 space-y-2">
                  {step.tools.map((tool, toolIndex) => {
                    const toolKey = `${step.round}-${toolIndex}`
                    const isToolExpanded = expandedTools.has(toolKey)

                    return (
                      <div key={toolIndex} className="border border-slate-200 rounded-lg bg-white overflow-hidden">
                        <button
                          onClick={() => toggleTool(toolKey)}
                          className="w-full flex items-center justify-between p-2 hover:bg-slate-50 transition-colors"
                        >
                          <div className="flex items-center space-x-2">
                            <Wrench className="w-3 h-3 text-blue-500" />
                            <span className="text-xs font-medium text-slate-700">{tool.name}</span>
                            {tool.status === 'completed' && (
                              <CheckCircle className="w-3 h-3 text-emerald-500" />
                            )}
                            {tool.status === 'running' && (
                              <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                            )}
                          </div>
                          {tool.result && (
                            isToolExpanded ? 
                              <ChevronDown className="w-3 h-3 text-slate-400" /> :
                              <ChevronRight className="w-3 h-3 text-slate-400" />
                          )}
                        </button>

                        {isToolExpanded && tool.result && (
                          <div className="p-2 bg-slate-50 border-t border-slate-200">
                            <pre className="text-xs text-slate-600 whitespace-pre-wrap overflow-x-auto max-h-40 overflow-y-auto">
                              {tool.result}
                            </pre>
                          </div>
                        )}
                      </div>
                    )
                  })}

                  {step.reasoning && (
                    <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center space-x-2 mb-1">
                        <Brain className="w-3 h-3 text-blue-500" />
                        <span className="text-xs font-medium text-blue-700">推理</span>
                      </div>
                      <p className="text-xs text-blue-600">{step.reasoning}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {isRunning && steps.length === 0 && (
          <div className="flex items-center justify-center py-4 space-x-2">
            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
            <span className="text-sm text-slate-500">正在思考...</span>
          </div>
        )}
      </div>
    </div>
  )
}
