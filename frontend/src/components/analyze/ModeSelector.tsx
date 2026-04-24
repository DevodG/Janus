interface ModeSelectorProps {
  value: 'solo' | 'standard' | 'deep' | undefined;
  onChange: (value: 'solo' | 'standard' | 'deep' | undefined) => void;
  disabled?: boolean;
}

const modes = [
  { value: undefined, label: 'Auto', description: 'Let the system decide' },
  { value: 'solo' as const, label: 'Solo', description: 'Single agent, fast' },
  { value: 'standard' as const, label: 'Standard', description: 'Multi-agent pipeline' },
  { value: 'deep' as const, label: 'Deep', description: 'Full analysis with verification' },
];

export default function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
      <label className="block text-sm font-medium text-gray-300 mb-3">
        Execution Mode (Optional)
      </label>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {modes.map((mode) => (
          <button
            key={mode.label}
            onClick={() => onChange(mode.value)}
            disabled={disabled}
            className={`p-4 rounded border transition-colors ${
              value === mode.value
                ? 'border-blue-500 bg-blue-900/30 text-blue-400'
                : 'border-gray-700 bg-gray-800/50 text-gray-300 hover:border-gray-600'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <div className="font-medium mb-1">{mode.label}</div>
            <div className="text-xs text-gray-500">{mode.description}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
