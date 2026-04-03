interface TaskInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export default function TaskInput({ value, onChange, onSubmit, disabled }: TaskInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      onSubmit();
    }
  };

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
      <label className="block text-sm font-medium text-gray-300 mb-3">
        Task Description
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Enter your analysis task... (e.g., 'Analyze Tesla stock performance' or 'What's the impact of recent Fed rate changes?')"
        className="w-full min-h-[160px] bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed resize-y"
      />
      <p className="text-xs text-gray-500 mt-2">
        Tip: Press Cmd/Ctrl + Enter to submit
      </p>
    </div>
  );
}
