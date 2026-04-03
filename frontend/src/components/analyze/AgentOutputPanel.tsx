import type { AgentOutput } from '@/lib/types';

interface AgentOutputPanelProps {
  output: AgentOutput;
}

export default function AgentOutputPanel({ output }: AgentOutputPanelProps) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-200 capitalize">
          {output.agent}
        </h4>
        {output.confidence > 0 && (
          <span className="text-xs text-gray-500">
            Confidence: {(output.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <div className="text-sm text-gray-300 whitespace-pre-wrap">
        {output.summary || 'No output'}
      </div>
    </div>
  );
}
