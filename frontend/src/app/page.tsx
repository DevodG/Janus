'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, Zap, ArrowUp, Brain, MessageSquare, ShieldAlert, ChevronRight } from 'lucide-react';
import { apiClient } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────
interface Message {
  id: string;
  role: 'user' | 'janus';
  content: string;
  timestamp: Date;
  metadata?: {
    domain?: string;
    queryType?: string;
    elapsed?: number;
    confidence?: number;
    routeInfo?: { domain_pack?: string; execution_mode?: string; complexity?: string; intent?: string };
    research?: any;
    finance?: any;
    simulation?: any;
    planner?: any;
    verifier?: any;
  };
}

// ─── Janus Orb ────────────────────────────────────────────
function JanusOrb({ size = 36, thinking = false }: { size?: number; thinking?: boolean }) {
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          background: 'radial-gradient(circle at 35% 35%, #818cf8, #4f46e5 55%, #1e1b4b 100%)',
          boxShadow: thinking
            ? '0 0 24px rgba(99,102,241,0.5), 0 0 48px rgba(99,102,241,0.2)'
            : '0 0 12px rgba(99,102,241,0.25)',
        }}
        animate={thinking ? { scale: [1, 1.1, 1] } : { scale: 1 }}
        transition={{ duration: 1.5, repeat: thinking ? Infinity : 0, ease: 'easeInOut' }}
      />
      {thinking && (
        <>
          <div
            className="absolute inset-[-4px] rounded-full border border-indigo-400/30"
            style={{ borderTopColor: 'transparent', borderBottomColor: 'transparent', animation: 'spin 2s linear infinite' }}
          />
          <div
            className="absolute inset-[-8px] rounded-full border border-violet-400/15"
            style={{ borderLeftColor: 'transparent', borderRightColor: 'transparent', animation: 'spin 3s linear infinite reverse' }}
          />
        </>
      )}
    </div>
  );
}

// ─── Typewriter ───────────────────────────────────────────
function Typewriter({ text, speed = 8, onComplete }: { text: string; speed?: number; onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);
  const completed = useRef(false);

  useEffect(() => {
    idx.current = 0;
    setDisplayed('');
    completed.current = false;

    const iv = setInterval(() => {
      if (idx.current < text.length) {
        // Write multiple characters per tick for speed
        const chunk = text.slice(idx.current, idx.current + 3);
        setDisplayed(p => p + chunk);
        idx.current += 3;
      } else {
        clearInterval(iv);
        if (!completed.current) {
          completed.current = true;
          onComplete?.();
        }
      }
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed, onComplete]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="inline-block w-0.5 h-4 bg-indigo-400/70 ml-0.5 animate-pulse align-middle" />
      )}
    </span>
  );
}

// ─── Thinking Indicator ───────────────────────────────────
const STAGES = [
  'Routing to switchboard...',
  'Research agent scanning...',
  'Cross-referencing sources...',
  'Synthesizing analysis...',
];

function ThinkingIndicator({ stage }: { stage: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex items-start gap-3 max-w-[768px]"
    >
      <JanusOrb size={32} thinking />
      <div className="pt-1">
        <motion.p
          key={stage}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-sm text-gray-400"
        >
          {stage}
        </motion.p>
        <div className="flex items-center gap-1 mt-2">
          {[0, 1, 2].map(i => (
            <motion.div
              key={i}
              className="w-1 h-1 rounded-full bg-indigo-400"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Message Bubble ───────────────────────────────────────
function MessageBubble({ message, isLatest }: { message: Message; isLatest: boolean }) {
  const isUser = message.role === 'user';

  let content = message.content;
  let thoughtProcess = '';
  // Extract <think>...</think> block via regex to simulate Claude 3.7
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
  if (thinkMatch) {
    thoughtProcess = thinkMatch[1].trim();
    content = content.replace(thinkMatch[0], '').trim();
  }

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end mb-4"
      >
        <div className="bg-[#2b2a2a] px-5 py-3 max-w-[600px] rounded-2xl rounded-tr-sm">
          <p className="text-[15px] text-[#ececec] leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>
      </motion.div>
    );
  }

  const meta = message.metadata || {};
  const { routeInfo, research, finance, planner } = meta;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3 max-w-[768px] mb-6"
    >
      <div className="mt-1 shrink-0 bg-transparent border border-white/10 rounded-md p-1.5 flex items-center justify-center bg-[#1e1e1e]">
        <Sparkles size={16} className="text-[#D97757]" />
      </div>
      <div className="flex-1 min-w-0">
        {/* Route metadata pills */}
        {routeInfo && (
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            {routeInfo.domain_pack && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium text-[#D97757] bg-[#D97757]/10 border border-[#D97757]/20">
                {routeInfo.domain_pack}
              </span>
            )}
            {routeInfo.execution_mode && (
              <span className="px-2 py-0.5 rounded-full text-[11px] text-gray-400 bg-white/[0.04] border border-white/[0.06]">
                {routeInfo.execution_mode}
              </span>
            )}
            {meta.elapsed && (
              <span className="text-[11px] text-gray-500">
                {meta.elapsed}s
              </span>
            )}
          </div>
        )}

        {/* Thought Process Accordion */}
        {(thoughtProcess || routeInfo || research) && (
          <details open className="mb-4 bg-white/[0.02] border border-white/[0.06] rounded-xl overflow-hidden group">
            <summary className="px-4 py-2.5 text-[12px] font-medium text-gray-400 cursor-pointer hover:text-gray-300 hover:bg-white/[0.02] flex items-center gap-2 select-none transition-colors">
              <Brain size={14} className="group-open:text-[#D97757] transition-colors" /> Thought Process
            </summary>
            
            <div className="px-5 py-4 text-[13px] text-gray-400 font-mono border-t border-white/[0.06] bg-black/20 whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
              
              {/* Architectural Trace */}
              {routeInfo && (
                <div className="mb-4 text-[#D97757]/80">
                  <span className="opacity-70">◆ </span> Routing query to <span className="text-[#ececec]">{routeInfo.domain_pack}</span> domain 
                  (Intent: "{routeInfo.intent || 'analysis'}")
                </div>
              )}
              
              {research?.summary && (
                <div className="mb-4 text-emerald-400/80">
                  <span className="opacity-70">◆ </span> Web & Knowledge Sweep Complete
                  <div className="pl-4 mt-1 border-l border-emerald-400/20 text-[12px] text-gray-500">
                    Sources retrieved: {research.sources?.length || 0}<br/>
                    {research.key_facts?.length ? `Extracted ${research.key_facts.length} key facts.` : ''}
                  </div>
                </div>
              )}

              {finance?.tickers && Object.keys(finance.tickers).length > 0 && (
                <div className="mb-4 text-blue-400/80">
                  <span className="opacity-70">◆ </span> Gathered financial market data for: {Object.keys(finance.tickers).join(', ')}
                </div>
              )}

              {planner?.plan && (
                <div className="mb-4 text-purple-400/80 border-b border-white/[0.04] pb-4">
                  <span className="opacity-70">◆ </span> Executed analytical reasoning graph
                </div>
              )}

              {/* LLM Extended Thinking Trace */}
              {thoughtProcess && (
                <div>
                  <div className="text-gray-500 mb-2 uppercase tracking-wide text-[10px]">Internal Cognitive Trace</div>
                  {thoughtProcess}
                </div>
              )}
              
            </div>
          </details>
        )}

        {/* Response content */}
        <div className="text-[15px] text-[#d1d5db] leading-[1.7] whitespace-pre-wrap">
          {isLatest ? (
            <Typewriter text={content} speed={6} />
          ) : (
            content
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ─── Suggested Prompts ────────────────────────────────────
const SUGGESTED = [
  'Analyze the impact of rising interest rates on tech stocks',
  'What is the current market sentiment around AI companies?',
  'Compare Reliance vs TCS as long-term investments',
  'Explain how quantitative tightening affects emerging markets',
];

function EmptyState({ onSelect, onOpenGuardian }: { onSelect: (q: string) => void, onOpenGuardian: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="flex flex-col items-center justify-center h-full px-4"
    >
      <JanusOrb size={56} />
      <h2 className="mt-8 text-xl font-light text-gray-200 tracking-wide text-center">
        What can I research for you?
      </h2>
      <p className="mt-2 text-sm text-gray-600 max-w-md text-center">
        Multi-agent intelligence pipeline — switchboard routes your query through research, analysis, and synthesis.
      </p>

      {/* Dedicated Scam Guardian Section */}
      <div className="w-full max-w-xl mt-10">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onOpenGuardian}
          className="w-full p-4 rounded-3xl bg-indigo-600/10 border border-indigo-500/20 flex items-center gap-4 group hover:bg-indigo-600/20 transition-all mb-4"
        >
          <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <ShieldAlert size={24} className="text-white" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-indigo-400 group-hover:text-indigo-300">Scam Guardian Module</h3>
            <p className="text-[11px] text-gray-500">Forensic threat detection for messages, URLs, and suspicious files.</p>
          </div>
          <ChevronRight size={18} className="ml-auto text-gray-600 group-hover:text-indigo-400" />
        </motion.button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl">
        {SUGGESTED.map(q => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="text-left px-4 py-3 rounded-2xl border border-white/[0.06] hover:border-white/[0.12] hover:bg-white/[0.03] transition-all group"
          >
            <p className="text-[13px] text-gray-400 group-hover:text-gray-200 transition-colors leading-snug">
              {q}
            </p>
          </button>
        ))}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════
//  MAIN CHAT PAGE
// ═══════════════════════════════════════════════════════════
export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingStage, setThinkingStage] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const latestMsgId = useRef<string | null>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, isThinking]);

  // Thinking stage rotation
  useEffect(() => {
    if (!isThinking) return;
    const iv = setInterval(() => setThinkingStage(p => (p + 1) % STAGES.length), 2500);
    return () => clearInterval(iv);
  }, [isThinking]);

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isThinking) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);
    setThinkingStage(0);

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    try {
      const result = await apiClient.run(text.trim());

      const finalAnswer = result.final_answer || result.final?.response || result.final?.summary || 'No analysis could be generated.';

      const janusMsg: Message = {
        id: `j-${Date.now()}`,
        role: 'janus',
        content: finalAnswer,
        timestamp: new Date(),
        metadata: {
          domain: result.domain,
          queryType: result.query_type,
          elapsed: result.elapsed_seconds,
          confidence: result.final?.confidence,
          routeInfo: result.route,
          research: result.research,
          finance: result.finance,
          simulation: result.simulation,
          planner: result.planner,
        },
      };
      latestMsgId.current = janusMsg.id;
      setMessages(prev => [...prev, janusMsg]);
    } catch (err) {
      const errStr = err instanceof Error ? err.message : String(err);
      const is429 = errStr.includes('429') || errStr.toLowerCase().includes('rate limit') || errStr.toLowerCase().includes('too many');
      const errorMsg: Message = {
        id: `e-${Date.now()}`,
        role: 'janus',
        content: is429
          ? 'Rate limited by OpenRouter (429). The free API tier has usage caps. Please wait 30-60 seconds and try again — the backend will auto-retry with backoff.'
          : `I encountered an error processing your request: ${errStr.slice(0, 200)}. Please check that the backend is running and try again.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsThinking(false);
    }
  }, [isThinking]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const isEmpty = messages.length === 0 && !isThinking;

  return (
    <div className="h-full flex overflow-hidden bg-[#0c0c0c]">
      <div className="flex-1 flex flex-col min-w-0 bg-[#0c0c0c]">
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Conversation area */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto pt-4">
            {isEmpty ? (
              <EmptyState 
                onSelect={(q) => { setInput(q); sendMessage(q); }} 
                onOpenGuardian={() => router.push('/guardian/intake')}
              />
            ) : (
              <div className="max-w-[860px] mx-auto px-4 py-8 space-y-6">
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    isLatest={msg.id === latestMsgId.current && msg.role === 'janus'}
                  />
                ))}
                <AnimatePresence>
                  {isThinking && <ThinkingIndicator stage={STAGES[thinkingStage]} />}
                </AnimatePresence>
              </div>
            )}
          </div>

          {/* Input bar */}
          <div className="shrink-0 border-t border-white/[0.04] px-4 py-6">
            <div className="max-w-[768px] mx-auto">
              <div className="input-bar flex items-end gap-2 px-4 py-2 bg-[#181818] rounded-3xl border border-white/[0.06] shadow-xl">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  disabled={isThinking}
                  placeholder="Message Janus..."
                  rows={1}
                  className="flex-1 bg-transparent text-[14px] text-gray-200 placeholder-gray-600 resize-none focus:outline-none disabled:opacity-40 leading-relaxed py-1.5 max-h-40"
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => sendMessage(input)}
                  disabled={isThinking || !input.trim()}
                  className="p-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-all shrink-0 mb-0.5"
                >
                  <ArrowUp size={18} />
                </motion.button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
