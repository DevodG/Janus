import Link from 'next/link';
import type { CaseRecord } from '@/lib/types';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';

interface CaseDetailProps {
  case_: CaseRecord;
}

export default function CaseDetail({ case_ }: CaseDetailProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Case Details</h1>
        <p className="text-gray-400 font-mono text-sm">{case_.case_id}</p>
      </div>

      <Card title="User Input">
        <p className="text-gray-200">{case_.user_input}</p>
      </Card>

      {case_.route && (
        <Card title="Routing Decision">
          <div className="space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge variant="info">{case_.route.execution_mode}</Badge>
              {case_.route.domain_pack && case_.route.domain_pack !== 'general' && (
                <Badge variant="default">{case_.route.domain_pack}</Badge>
              )}
              <Badge variant="default">{case_.route.complexity}</Badge>
              <Badge variant="default">{case_.route.task_family}</Badge>
              <Badge variant="default">{case_.route.risk_level}</Badge>
            </div>
          </div>
        </Card>
      )}

      {case_.final_answer && (
        <Card title="Final Answer">
          <div className="prose prose-invert max-w-none">
            <p className="text-gray-200 whitespace-pre-wrap">{case_.final_answer}</p>
          </div>
        </Card>
      )}

      {case_.outputs && case_.outputs.length > 0 && (
        <Card title="Agent Outputs">
          <div className="space-y-4">
            {case_.outputs.map((output, index) => (
              <div key={index} className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
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
            ))}
          </div>
        </Card>
      )}

      {case_.simulation_id && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-300 mb-1">
                Associated Simulation
              </p>
              <p className="text-xs text-gray-500 font-mono">{case_.simulation_id}</p>
            </div>
            <Link
              href={`/simulation/${case_.simulation_id}`}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm transition-colors"
            >
              View Simulation
            </Link>
          </div>
        </Card>
      )}

      <Card title="Metadata">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Case ID:</span>
            <p className="text-gray-200 font-mono mt-1">{case_.case_id}</p>
          </div>
          {case_.saved_at && (
            <div>
              <span className="text-gray-400">Saved At:</span>
              <p className="text-gray-200 mt-1">{new Date(case_.saved_at).toLocaleString()}</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
