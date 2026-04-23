import React from 'react';

type EvidenceItem = {
  source: string;
  signal: string;
  value?: string | number | boolean | null;
  severity: string;
  explanation: string;
};

type OfficialVerify = {
  brand?: string | null;
  instruction: string;
  official_site?: string | null;
};

type ResultPayload = {
  evidence?: EvidenceItem[];
  claimed_brand?: string | null;
  official_verify?: OfficialVerify | null;
  next_steps?: string[];
  breadcrumbs?: string[];
};

function badgeClasses(severity?: string) {
  switch ((severity || "").toLowerCase()) {
    case "high":
      return "bg-red-100 text-red-700 border-red-200";
    case "medium":
      return "bg-amber-100 text-amber-700 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}

export default function LiveEvidencePanel({ result }: { result: ResultPayload }) {
  const evidence = result.evidence || [];
  const steps = result.next_steps || [];
  const verify = result.official_verify;
  const crumbs = result.breadcrumbs || [];

  if (!evidence.length && !steps.length && !verify && !crumbs.length) return null;

  return (
    <div className="mt-6 space-y-4">
      {!!crumbs.length && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50/20 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold uppercase tracking-wider text-blue-500">Forensic Investigation Log</div>
            <div className="flex items-center gap-1.5">
              <div className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-[10px] font-bold text-blue-400 uppercase">Live Analysis Active</span>
            </div>
          </div>
          <div className="mt-3 space-y-1.5">
            {crumbs.map((crumb, idx) => (
              <div key={idx} className="flex gap-2 text-xs font-mono text-slate-500">
                <span className="text-blue-400 opacity-50">{idx + 1}.</span>
                <span className={idx === crumbs.length - 1 ? "text-blue-600 font-bold" : ""}>
                  {crumb}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-blue-100/30">
             <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Janus Cognitive Synthesis</div>
             <p className="text-xs text-slate-600 leading-relaxed italic">
               Live infrastructure probe indicates a {crumbs.length > 5 ? "deeply obfuscated" : "partially masked"} network profile. 
               Cross-referencing global threat feeds with {evidence.length} forensic hits. 
               {verify ? `Defending authenticity for ${verify.brand}.` : "Neutralizing unidentified infrastructure."}
             </p>
          </div>
        </div>
      )}
      {verify && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-slate-500">Official verification</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {verify.brand || result.claimed_brand || "Official route"}
          </div>
          <p className="mt-2 text-sm text-slate-700">{verify.instruction}</p>
          {verify.official_site && (
            <a
              href={verify.official_site}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-sm font-medium text-blue-600 hover:underline"
            >
              Open official site
            </a>
          )}
        </div>
      )}

      {!!evidence.length && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-slate-500">Live evidence</div>
          <div className="mt-3 space-y-3">
            {evidence.map((item, idx) => (
              <div key={`${item.source}-${idx}`} className="rounded-xl border border-slate-200 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium text-slate-900">{item.source}</div>
                  <span className={`rounded-full border px-2 py-1 text-xs font-semibold ${badgeClasses(item.severity)}`}>
                    {item.severity}
                  </span>
                </div>
                <div className="mt-1 text-sm text-slate-700">{item.explanation}</div>
                {item.value !== undefined && item.value !== null && (
                  <div className="mt-2 text-xs text-slate-500">Signal value: {String(item.value)}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!!steps.length && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold text-slate-500">What to do now</div>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {steps.map((step, idx) => (
              <li key={idx} className="flex gap-2">
                <span className="mt-[2px] text-slate-400">•</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
