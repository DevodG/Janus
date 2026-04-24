import { useState } from 'react';
import type { PromptInfo } from '@/lib/types';
import Card from '@/components/common/Card';
import ErrorMessage from '@/components/common/ErrorMessage';

interface PromptEditorProps {
  prompt: PromptInfo;
  onSave: (name: string, content: string) => Promise<void>;
}

export default function PromptEditor({ prompt, onSave }: PromptEditorProps) {
  const [content, setContent] = useState(prompt.content);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await onSave(prompt.name, content);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save prompt');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setContent(prompt.content);
    setError(null);
    setSuccess(false);
  };

  const hasChanges = content !== prompt.content;

  return (
    <Card title={`Edit ${prompt.name} Prompt`}>
      <div className="space-y-4">
        {error && <ErrorMessage message={error} />}
        {success && (
          <div className="bg-green-900/20 border border-green-800 rounded-lg p-4">
            <p className="text-green-400 text-sm">Prompt saved successfully!</p>
          </div>
        )}

        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          disabled={saving}
          className="w-full min-h-[500px] bg-gray-950 border border-gray-700 rounded px-4 py-3 text-gray-100 font-mono text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50 resize-y"
        />

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            onClick={handleReset}
            disabled={saving || !hasChanges}
            className="px-6 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
          >
            Reset
          </button>
        </div>

        <p className="text-xs text-gray-500">
          Changes will take effect immediately for new analysis requests
        </p>
      </div>
    </Card>
  );
}
