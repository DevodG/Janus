import type { CaseRecord } from '@/lib/types';
import CaseCard from './CaseCard';

interface CaseListProps {
  cases: CaseRecord[];
}

export default function CaseList({ cases }: CaseListProps) {
  return (
    <div className="space-y-4">
      {cases.map((case_) => (
        <CaseCard key={case_.case_id} case_={case_} />
      ))}
    </div>
  );
}
