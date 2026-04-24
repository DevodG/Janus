import Link from 'next/link';
import type { CaseRecord } from '@/lib/types';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import AgentOutputPanel from './AgentOutputPanel';

interface ResultViewerProps {
  result: CaseRecord;
}

export default function ResultViewer({ result }: ResultViewerProps) {
  return (
    <div className="space-y-6">
      {result.route && (
        <Card title="Analysis Complete">
          <div className="space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Badge variant="info">{result.route.execution_mode}</Badge>
              {result.route.domain_pack && result.route.domain_pack !== 'general' && (
                <Badge variant="default">{result.route.domain_pack}</Badge>
              )}
              <Badge variant="default">{result.route.complexity}</Badge>
              <Badge variant="default">{result.route.task_family}</Badge>
            </div>

            <div className="text-sm text-gray-400">
              <span className="font-medium">Case ID:</span>{' '}
              <Link href={`/cases/${result.case_id}`} className="text-blue-400 hover:underline">
                {result.case_id}
              </Link>
            </div>
          </div>
        </Card>
      )}

      {result.final_answer && (
        <Card title="Final Answer">
          <div className="prose prose-invert max-w-none">
            <p className="text-gray-200 whitespace-pre-wrap">{result.final_answer}</p>
          </div>
        </Card>
      )}

      {result.outputs && result.outputs.length > 0 && (
        <Card title="Agent Outputs">
          <div className="space-y-4">
            {result.outputs.map((output, index) => (
              <AgentOutputPanel key={index} output={output} />
            ))}
          </div>
        </Card>
      )}

      {result.simulation_id && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-300 mb-1">
                Simulation Available
              </p>
              <p className="text-xs text-gray-500">
                This case has an associated simulation
              </p>
            </div>
            <Link
              href={`/simulation/${result.simulation_id}`}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm transition-colors"
            >
              View Simulation
            </Link>
          </div>
        </Card>
      )}
    </div>
  );
}
