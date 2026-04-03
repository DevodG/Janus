export default function Header() {
  return (
    <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              MiroOrg
            </div>
            <div className="text-xs text-gray-500 font-mono">v1.1</div>
          </div>
          <div className="text-sm text-gray-400">
            AI Financial Intelligence System
          </div>
        </div>
      </div>
    </header>
  );
}
