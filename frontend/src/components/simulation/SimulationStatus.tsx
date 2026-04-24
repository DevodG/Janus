import Badge from '@/components/common/Badge';

interface SimulationStatusProps {
  status: 'submitted' | 'running' | 'completed' | 'failed';
}

const statusConfig = {
  submitted: { variant: 'default' as const, label: 'Submitted' },
  running: { variant: 'info' as const, label: 'Running' },
  completed: { variant: 'success' as const, label: 'Completed' },
  failed: { variant: 'error' as const, label: 'Failed' },
};

export default function SimulationStatus({ status }: SimulationStatusProps) {
  const config = statusConfig[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
