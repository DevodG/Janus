import type { PromptInfo } from '@/lib/types';
import Card from '@/components/common/Card';

interface PromptListProps {
  prompts: PromptInfo[];
  selectedPrompt: PromptInfo | null;
  onSelect: (prompt: PromptInfo) => void;
}

export default function PromptList({ prompts, selectedPrompt, onSelect }: PromptListProps) {
  return (
    <Card title="Prompts">
      <div className="space-y-2">
        {prompts.map((prompt) => (
          <button
            key={prompt.name}
            onClick={() => onSelect(prompt)}
            className={`w-full text-left px-4 py-3 rounded transition-colors ${
              selectedPrompt?.name === prompt.name
                ? 'bg-blue-900/30 text-blue-400 border border-blue-800'
                : 'bg-gray-800/50 text-gray-300 hover:bg-gray-800 border border-transparent'
            }`}
          >
            <div className="font-medium capitalize">{prompt.name}</div>
          </button>
        ))}
      </div>
    </Card>
  );
}
