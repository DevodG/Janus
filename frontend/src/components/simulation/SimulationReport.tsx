import Link from 'next/link';
import type { SimulationRecord } from '@/lib/types';
import Card from '@/components/common/Card';
import SimulationStatus from './SimulationStatus';

interface SimulationReportProps {
  simulation: SimulationRecord;
}

export default function SimulationReport({ simulation }: SimulationReportProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">{simulation.title}</h1>
        <p className="text-gray-400 font-mono text-sm">{simulation.simulation_id}</p>
      </div>

      <Card title="Simulation Details">
        <div className="space-y-4">
          <div>
            <span className="text-sm text-gray-400">Status:</span>
            <div className="mt-1">
              <SimulationStatus status={simulation.status} />
            </div>
          </div>

          <div>
            <span className="text-sm text-gray-400">Prediction Goal:</span>
            <p className="text-gray-200 mt-1">{simulation.prediction_goal}</p>
          </div>

          <div>
            <span className="text-sm text-gray-400">Created:</span>
            <p className="text-gray-200 mt-1">N/A</p>
          </div>

          {simulation.case_id && (
            <div>
              <span className="text-sm text-gray-400">Linked Case:</span>
              <div className="mt-1">
                <Link
                  href={`/cases/${simulation.case_id}`}
                  className="text-blue-400 hover:underline font-mono text-sm"
                >
                  {simulation.case_id}
                </Link>
              </div>
            </div>
          )}
        </div>
      </Card>

      {simulation.status === 'completed' && simulation.report && (
        <Card title="Simulation Report">
          <div className="prose prose-invert max-w-none">
            <p className="text-gray-200 whitespace-pre-wrap">{simulation.report}</p>
          </div>
        </Card>
      )}

      {simulation.status === 'running' && (
        <Card>
          <div className="text-center py-8">
            <p className="text-gray-400 mb-2">Simulation is currently running...</p>
            <p className="text-sm text-gray-500">Check back later for results</p>
          </div>
        </Card>
      )}

      {simulation.status === 'failed' && (
        <Card>
          <div className="text-center py-8">
            <p className="text-red-400 mb-2">Simulation failed</p>
            <p className="text-sm text-gray-500">Please try creating a new simulation</p>
          </div>
        </Card>
      )}
    </div>
  );
}
