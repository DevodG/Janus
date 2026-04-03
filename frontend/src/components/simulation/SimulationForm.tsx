import { useState } from 'react';
import Card from '@/components/common/Card';

interface SimulationFormProps {
  onSubmit: (title: string, seedText: string, predictionGoal: string, caseId?: string) => void;
  loading: boolean;
}

export default function SimulationForm({ onSubmit, loading }: SimulationFormProps) {
  const [title, setTitle] = useState('');
  const [seedText, setSeedText] = useState('');
  const [predictionGoal, setPredictionGoal] = useState('');
  const [caseId, setCaseId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(title, seedText, predictionGoal, caseId || undefined);
  };

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Simulation Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={loading}
            placeholder="e.g., Tesla Stock Price Prediction"
            className="w-full bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Seed Context
          </label>
          <textarea
            value={seedText}
            onChange={(e) => setSeedText(e.target.value)}
            disabled={loading}
            placeholder="Provide background context for the simulation... (e.g., 'Tesla reported Q1 earnings with 10% revenue decline. Competition from BYD is intensifying.')"
            className="w-full min-h-[100px] bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 resize-y"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Prediction Goal
          </label>
          <textarea
            value={predictionGoal}
            onChange={(e) => setPredictionGoal(e.target.value)}
            disabled={loading}
            placeholder="What do you want to predict? (e.g., 'Predict Tesla stock price movement over the next 30 days')"
            className="w-full min-h-[100px] bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 resize-y"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Case ID <span className="text-gray-500">(Optional)</span>
          </label>
          <input
            type="text"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            disabled={loading}
            placeholder="Link to an existing analysis case"
            className="w-full bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !title.trim() || !seedText.trim() || !predictionGoal.trim()}
          className="w-full px-6 py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
        >
          {loading ? 'Creating Simulation...' : 'Create Simulation'}
        </button>
      </form>
    </Card>
  );
}
