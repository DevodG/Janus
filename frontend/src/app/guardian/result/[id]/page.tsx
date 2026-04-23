'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { AlertTriangle, CheckCircle, ShieldAlert, Phone, Globe, CreditCard, Tag, Activity } from 'lucide-react';

import { guardianClient } from '@/lib/api';

export default function ResultPage() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const result = await guardianClient.getEvent(id as string);
        setData(result);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [id]);

  if (loading) return <div className="p-20 text-center">Loading Forensic Intelligence...</div>;
  if (!data) return <div className="p-20 text-center text-red-400">Result not found or analysis failed.</div>;

  const getRiskColor = (score: number) => {
    if (score >= 80) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (score >= 40) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
    return 'text-green-500 bg-green-500/10 border-green-500/20';
  };

  return (
    <div className="max-w-5xl mx-auto py-12 px-6">
      <div className="grid md:grid-cols-3 gap-8">
        
        {/* Left Column: Risk Meter & Decision */}
        <div className="md:col-span-1 space-y-6">
          <div className={`p-8 rounded-3xl border text-center ${getRiskColor(data.risk_score)}`}>
            <h2 className="text-sm uppercase tracking-widest font-bold mb-2 opacity-70">Forensic Verdict</h2>
            <div className="text-6xl font-black mb-4">{data.decision}</div>
            <div className="h-4 bg-black/40 rounded-full overflow-hidden mb-4">
              <div 
                className={`h-full transition-all duration-1000 ${data.risk_score >= 80 ? 'bg-red-500' : 'bg-yellow-500'}`}
                style={{ width: `${data.risk_score}%` }}
              />
            </div>
            <p className="text-lg font-semibold">Risk Index: {data.risk_score}%</p>
          </div>

          <div className="bg-gray-900/50 border border-gray-800 p-6 rounded-2xl">
            <h3 className="font-bold mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-blue-500" />
              Reasoning Layer
            </h3>
            <ul className="space-y-3">
              {data.reasons.map((reason: string, i: number) => (
                <li key={i} className="flex gap-3 text-sm text-gray-300">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          {/* Journey Depth */}
          {data.similarity?.matches?.length > 0 && (
             <div className="bg-blue-600/10 border border-blue-500/30 p-6 rounded-2xl">
                <h3 className="text-sm font-bold text-blue-400 mb-2 uppercase">Semantic Match</h3>
                <p className="text-sm text-gray-400">This content is {data.similarity.matches[0].similarity}% similar to a known scam family seen on {new Date(data.similarity.matches[0].ts).toLocaleDateString()}.</p>
             </div>
          )}
        </div>

        {/* Right Column: Signal Breakdown */}
        <div className="md:col-span-2 space-y-6">
          {/* MMSA Dissonance Card (Depth) */}
          {data.similarity?.mmsa && (
            <div className="bg-purple-900/30 border border-purple-500/30 p-8 rounded-3xl relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-20">
                  <Activity className="w-16 h-16 text-purple-400" />
               </div>
               <h3 className="text-xl font-bold mb-4 text-purple-400">Multi-Modal Dissonance Detected</h3>
               <div className="flex gap-8 items-center">
                  <div className="text-4xl font-black">{Math.round(data.similarity.mmsa.dissonance_score * 100)}%</div>
                  <div className="flex-1 space-y-2">
                      {data.similarity.mmsa.analysis_tags.map((tag: string, i: number) => (
                        <span key={i} className="inline-block px-3 py-1 bg-purple-500/20 rounded-full text-xs font-bold mr-2">{tag}</span>
                      ))}
                      <p className="text-sm text-gray-400 mt-2">Dissonance engine detected conflict between verbal content and emotional delivery.</p>
                  </div>
               </div>
            </div>
          )}
          <div className="bg-gray-900/50 border border-gray-800 p-8 rounded-3xl">
            <h3 className="text-xl font-bold mb-6">Signal Intensity</h3>
            <div className="grid grid-cols-2 gap-8">
              {Object.entries(data.intent).map(([key, val]: [string, any]) => (
                <div key={key}>
                  <div className="flex justify-between text-sm mb-2 uppercase tracking-wide opacity-60">
                    <span>{key}</span>
                    <span>{Math.round(val * 100)}%</span>
                  </div>
                  <div className="h-2 bg-black/40 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all duration-1000"
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
             <DataCard icon={<Phone className="text-blue-400" />} title="Identified Phones" items={data.entities.phones} />
             <DataCard icon={<Globe className="text-purple-400" />} title="Suspicious Domains" items={data.entities.domains} />
             <DataCard icon={<CreditCard className="text-green-400" />} title="Payment Endpoints" items={data.entities.upi_ids} />
             <DataCard icon={<Tag className="text-yellow-400" />} title="Referenced Brands" items={data.entities.brands} />
          </div>
        </div>

      </div>
    </div>
  );
}

function DataCard({ icon, title, items }: any) {
  return (
    <div className="bg-gray-900/50 border border-gray-800 p-6 rounded-2xl">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h4 className="font-semibold">{title}</h4>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.length > 0 ? items.map((item: string, i: number) => (
          <span key={i} className="px-3 py-1 bg-black/40 border border-gray-800 rounded-lg text-xs font-mono text-gray-300">
            {item}
          </span>
        )) : <span className="text-xs text-gray-600">No signals detected</span>}
      </div>
    </div>
  );
}
