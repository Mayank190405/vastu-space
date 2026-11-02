import React from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import { ScanPipeline, currentStages, isSubmitted, pipelineState, stageLabel, toneClasses } from './pipelineState';

interface Props { projectId: string; entries: ScanPipeline[]; loading: boolean; error: string | null; refresh: () => void; compact?: boolean; updatedAt?: Date | null }
export const ProjectPipelinePanel: React.FC<Props> = ({ projectId, entries, loading, error, refresh, compact, updatedAt }) => {
  const submitted = entries.filter(e => isSubmitted(e.session)).sort((a,b) => Date.parse(b.session.created_at) - Date.parse(a.session.created_at));
  const visible = compact ? submitted.slice(0, 3) : submitted;
  return <section className="rounded-2xl border border-[#D1C2A5] bg-white p-5 md:p-6 space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="flex items-center gap-2 text-lg font-bold text-[#1F150D]"><Activity className="h-5 w-5 text-[#8F6834]" />Scan pipeline</h2>
        <p className="text-xs text-[#695541] mt-1">{updatedAt ? `Updated ${updatedAt.toLocaleTimeString()} · refreshes every 5 seconds` : 'Submitted scans and their persisted processing stages'}</p></div>
      <div className="flex gap-3 items-center"><button aria-label="Refresh pipeline status" onClick={refresh} className="p-2 border rounded-lg hover:bg-stone-50"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
        {compact && <Link to={`/projects/${projectId}/pipelines`} className="text-sm font-semibold text-[#8F6834] flex items-center gap-1">Pipeline dashboard<ArrowUpRight className="w-4 h-4" /></Link>}</div>
    </div>
    {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error} <button onClick={refresh} className="underline font-semibold">Retry status check</button></div>}
    {loading && !entries.length ? <div className="flex gap-2 text-sm text-stone-500"><Loader2 className="w-4 h-4 animate-spin" />Loading scans…</div> : !submitted.length && !error ? <p className="text-sm text-stone-500 py-4">No submitted scans yet. Your scan will appear here when the mobile upload begins.</p> : null}
    <div className="space-y-3">{visible.map(scan => {
      const state = pipelineState(scan), stages = currentStages(scan), completed = stages.filter(s => s.status === 'COMPLETED').length;
      return <article key={scan.session.id} className="rounded-xl border border-stone-200 bg-[#FAF7F2] p-4 space-y-3">
        <div className="flex flex-wrap justify-between gap-3"><div><h3 className="font-semibold text-[#1F150D]">{scan.session.room_name}</h3><p className="text-xs text-stone-500 mt-1">{new Date(scan.session.created_at).toLocaleString()} · {scan.session.operator_name || 'Mobile scan'}</p></div>
          <span className={`self-start rounded-full border px-3 py-1 text-xs font-semibold ${toneClasses[state.tone]}`}>{state.label}</span></div>
        {state.stage && <p className="text-sm text-stone-700">{state.stage.status === 'COMPLETED' ? 'Latest confirmed stage' : 'Current stage'}: <strong>{stageLabel(state.stage.stage_name)}</strong></p>}
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-stone-500"><span className="flex items-center gap-1">{scan.session.upload_verified_at && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}{scan.session.upload_verified_at ? 'Video verified in storage' : 'Video upload in progress'}</span><span>{completed} / {stages.length} stages recorded complete</span></div>
        {(scan.job?.error_message || state.stage?.error_details) && <p className="text-xs text-rose-700 break-words">{scan.job?.error_message || state.stage?.error_details}</p>}
        <div className="flex flex-wrap justify-between items-center gap-2 pt-2 border-t border-stone-200"><span className="text-[11px] font-mono text-stone-500 break-all">{scan.session.id}</span><Link to={`/projects/${projectId}/pipelines/${scan.session.id}`} className="text-sm font-bold text-[#8F6834] flex items-center gap-1">Open scan dashboard<ArrowUpRight className="w-4 h-4" /></Link></div>
      </article>;
    })}</div>
  </section>;
};
