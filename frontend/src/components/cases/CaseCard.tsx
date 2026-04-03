import Link from 'next/link';
import type { CaseRecord } from '@/lib/types';
import Badge from '@/components/common/Badge';

interface CaseCardProps {
  case_: CaseRecord;
}

export default function CaseCard({ case_ }: CaseCardProps) {
  return (
    <Link
      href={`/cases/${case_.case_id}`}
      className="block bg-gray-900/50 border border-gray-800 rounded-lg p-6 hover:border-gray-700 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-medium text-gray-200 line-clamp-2 flex-1">
          {case_.user_input}
        </h3>
        {case_.route?.execution_mode && (
          <Badge variant="info" className="ml-4 flex-shrink-0">
            {case_.route.execution_mode}
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap mb-3">
        {case_.route?.domain_pack && case_.route.domain_pack !== 'general' && (
          <Badge variant="default">{case_.route.domain_pack}</Badge>
        )}
        {case_.route?.complexity && (
          <Badge variant="default">{case_.route.complexity}</Badge>
        )}
        {case_.route?.task_family && (
          <Badge variant="default">{case_.route.task_family}</Badge>
        )}
        {case_.simulation_id && <Badge variant="warning">Has Simulation</Badge>}
      </div>

      <div className="flex items-center justify-between text-sm text-gray-500">
        <span>{case_.saved_at ? new Date(case_.saved_at).toLocaleString() : 'N/A'}</span>
        <span className="text-xs font-mono">{case_.case_id.slice(0, 8)}</span>
      </div>
    </Link>
  );
}
