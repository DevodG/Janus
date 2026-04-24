'use client';

import React, { useEffect, useState } from 'react';
import { GitBranch, Clock, ArrowRight, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

import { guardianClient } from '@/lib/api';

export default function JourneyPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await guardianClient.getHistory();
        setHistory(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="max-w-5xl mx-auto py-12 px-6">
      <div className="flex justify-between items-end mb-12">
        <div>
          <h1 className="text-4xl font-black mb-2">Scam Journey Graph</h1>
          <p className="text-gray-400">Visualization of linked scam events and repeating attack vectors.</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-blue-500">{history.length}</div>
          <div className="text-xs uppercase tracking-widest text-gray-500">Tracked Incidents</div>
        </div>
      </div>

      <div className="space-y-8">
        {history.length > 0 ? (
          history.map((event, i) => (
            <div key={event.id} className="relative flex gap-8">
              {/* Timeline Line */}
              {i !== history.length - 1 && (
                <div className="absolute left-6 top-12 bottom-0 w-px bg-gray-800" />
              )}
              
              <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 z-10 ${
                event.decision === 'BLOCK' ? 'bg-red-500/20 text-red-500' : 'bg-yellow-500/20 text-yellow-500'
              }`}>
                <Clock className="w-6 h-6" />
              </div>

              <Link 
                href={`/guardian/result/${event.id}`}
                className="flex-1 bg-gray-900/50 border border-gray-800 p-6 rounded-2xl hover:border-blue-500/50 transition-all group"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="text-xs font-mono text-gray-500 mb-1">{new Date(event.created_at || Date.now()).toLocaleString()}</div>
                    <h3 className="text-xl font-bold line-clamp-1">{event.text}</h3>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                    event.decision === 'BLOCK' ? 'bg-red-500/20 text-red-500' : 'bg-yellow-500/20 text-yellow-500'
                  }`}>
                    {event.decision}
                  </div>
                </div>

                <div className="flex gap-4 items-center">
                   <div className="flex -space-x-2">
                     {event.entities.phones.slice(0, 2).map((p: any, j: number) => (
                       <div key={j} className="w-8 h-8 rounded-full bg-blue-600 border-2 border-black flex items-center justify-center text-[10px] font-bold">P</div>
                     ))}
                     {event.entities.domains.slice(0, 2).map((d: any, j: number) => (
                       <div key={j} className="w-8 h-8 rounded-full bg-purple-600 border-2 border-black flex items-center justify-center text-[10px] font-bold">D</div>
                     ))}
                   </div>
                   <div className="text-sm text-gray-400">
                     {event.reasons[0]}
                   </div>
                   <ArrowRight className="w-5 h-5 ml-auto text-gray-600 group-hover:text-blue-500 transition-colors" />
                </div>
              </Link>
            </div>
          ))
        ) : (
          <div className="text-center py-20 bg-gray-900/30 rounded-3xl border border-dashed border-gray-800">
            <ShieldCheck className="w-16 h-16 text-gray-700 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-gray-500">No scams tracked yet.</h3>
            <p className="text-gray-600 mb-8">Start by analyzing a suspicious message in the Intake Hub.</p>
            <Link href="/guardian/intake" className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-500">
              Go to Intake Hub
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
