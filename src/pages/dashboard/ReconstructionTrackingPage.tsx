import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, AlertCircle, CheckCircle2, Circle, ExternalLink, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { CaptureSessionRecord, ConnectedDevice, PipelineStageRecord } from '../../types';
import { currentStages, PipelineJob, PipelineLog, pipelineState, stageLabel, terminalPipeline, toneClasses } from '../../components/pipeline/pipelineState';

export const ReconstructionTrackingPage: React.FC = () => {
  const { sessionId, projectId: routeProjectId } = useParams<{sessionId: string; projectId?: string}>();
  const [session, setSession] = useState<CaptureSessionRecord | null>(null);
  const [stages, setStages] = useState<PipelineStageRecord[]>([]);
  const [job, setJob] = useState<PipelineJob>();
  const [logs, setLogs] = useState<PipelineLog[]>([]);
  const [device, setDevice] = useState<ConnectedDevice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date>();
  const [revision, setRevision] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const refresh = () => setRevision(n => n + 1);

  useEffect(() => { setSession(null); setStages([]); setJob(undefined); setLogs([]); setDevice(null); }, [sessionId]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    setLoading(true);
    setError(null);
    const poll = async () => {
      try {
        if (!sessionId?.startsWith('sess_')) throw new Error('Open a valid capture session from the project pipeline dashboard.');
        if (document.visibilityState === 'hidden') { timer = setTimeout(poll, 3000); return; }
        const record = await api.getQRSession(sessionId);
        if (routeProjectId && record.project_id !== routeProjectId) throw new Error('This scan belongs to a different project.');
        const [stageRecords, jobRecord, jobLogs, devices] = await Promise.all([
          api.getPipelineStages(sessionId),
          record.job_id ? api.getJob(record.job_id) : Promise.resolve(undefined),
          record.job_id ? api.getJobLogs(record.job_id) : Promise.resolve([]),
          api.listDevices().catch(() => []),
        ]);
        if (!active) return;
        setSession(record); setStages(stageRecords || []); setJob(jobRecord); setLogs((jobLogs || []).slice(-100));
        setDevice(devices.find(d => d.current_session_id === record.id && d.device_uuid === record.device_id) || null);
        setUpdatedAt(new Date()); setError(null);
        if (!terminalPipeline({session: record, stages: stageRecords || [], job: jobRecord})) timer = setTimeout(poll, 3000);
      } catch (err: any) { if (active) setError(err.message || 'Unable to load scan status.'); }
      finally { if (active) setLoading(false); }
    };
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [sessionId, routeProjectId, revision]);

  const scan = session ? {session, stages, job} : null;
  const state = scan ? pipelineState(scan) : null;
  const visibleStages = scan ? currentStages(scan) : [];
  const completed = visibleStages.filter(s => s.status === 'COMPLETED').length;
  const projectId = session?.project_id || routeProjectId;
  const failure = job?.error_message || state?.stage?.error_details;
  const canRetry = job?.stage === 'failed';
  const onRetry = async () => {
    if (!sessionId || retrying) return;
    setRetrying(true);
    try { await api.retryCaptureProcessing(sessionId); refresh(); }
    catch (err: any) { setError(err.message); }
    finally { setRetrying(false); }
  };
  return <main className="min-h-screen bg-[#FAF7F2] text-[#1F150D] p-4 md:p-8"><div className="max-w-6xl mx-auto space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <Link to={projectId ? `/projects/${projectId}/pipelines` : '/dashboard/sessions'} className="inline-flex items-center gap-2 text-sm text-[#695541]"><ArrowLeft className="w-4 h-4" />{projectId ? 'Project pipelines' : 'Capture sessions'}</Link>
      <button onClick={refresh} className="flex items-center gap-2 rounded-xl bg-white border border-[#D1C2A5] px-4 py-2 text-sm"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh status</button>
    </div>
    <header className="rounded-2xl border border-[#D1C2A5] bg-white p-6 md:p-8 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-widest text-[#8F6834]">{session?.project_name || 'Scan processing'}</p><h1 className="text-3xl font-bold mt-2">{session?.room_name || 'Scan pipeline dashboard'}</h1><p className="text-sm text-[#695541] mt-2">Recording → verified upload → reconstruction → published viewer</p></div>
        {state && <span className={`rounded-full px-4 py-2 border text-sm font-semibold ${toneClasses[state.tone]}`}>{state.label}</span>}</div>
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-stone-500"><span>Session: <span className="font-mono">{sessionId}</span></span><span>{updatedAt ? `Last checked ${updatedAt.toLocaleTimeString()}` : 'Waiting for backend status'}</span><span>{scan && terminalPipeline(scan) ? 'Processing stopped · refresh to check again' : 'Updates every 3 seconds'}</span></div>
    </header>
    {error && <div role="alert" className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-sm text-rose-700">{error} <button onClick={refresh} className="underline font-bold ml-2">Retry status check</button>{updatedAt && <p className="text-xs mt-1">Showing the last received status.</p>}</div>}
    {loading && !session && <div className="flex gap-2 items-center text-stone-500"><Loader2 className="w-5 h-5 animate-spin" />Loading scan…</div>}
    {session && <>
      <div className="grid sm:grid-cols-3 gap-3">
        <Metric label="Video upload" value={session.upload_verified_at ? 'Storage verified' : session.upload_id ? 'Uploading' : 'Not submitted'} detail={session.upload_verified_at ? new Date(session.upload_verified_at).toLocaleString() : 'Waiting for server confirmation'} />
        <Metric label="Pipeline stages" value={`${completed} / ${visibleStages.length} complete`} detail={state?.stage ? stageLabel(state.stage.stage_name) : state?.label || 'Waiting'} />
        <Metric label="Connected device" value={device?.device_model || 'No current device presence'} detail={device ? `${device.device_os} · ${device.status} · heartbeat ${new Date(device.last_heartbeat_at).toLocaleTimeString()}` : 'Worker processing can continue after the phone disconnects'} />
      </div>
      {(failure || canRetry || state?.tone === 'retrying') && <section className="border border-amber-200 bg-amber-50 rounded-xl p-5 space-y-3"><h2 className="font-bold flex gap-2 items-center"><AlertCircle className="w-5 h-5" />{canRetry ? 'Processing needs attention' : 'Worker retry scheduled'}</h2><p className="text-sm break-words">{failure || 'The worker reported a failure and will retry. Inspect the execution log below.'}</p>{job?.error_code && <p className="text-xs font-mono">{job.error_code}</p>}{canRetry && <button onClick={onRetry} disabled={retrying} className="bg-[#8F6834] text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">{retrying ? 'Submitting retry…' : 'Retry failed processing'}</button>}</section>}
      <div className="grid lg:grid-cols-[1.1fr_1fr] gap-6 items-start">
        <section className="bg-white border border-[#D1C2A5] rounded-2xl p-5 space-y-4"><h2 className="font-bold text-lg">Processing stages</h2><p className="text-xs text-stone-500">Statuses come from persisted capture and worker events. Pending steps have no confirmed completion event.</p>
          {!visibleStages.length && <p className="text-sm text-stone-500">No pipeline events yet.</p>}
          <ol className="divide-y divide-stone-100">{visibleStages.map(stage => <li key={stage.id} className="py-3 space-y-1"><div className="flex justify-between gap-3 items-center"><div className="flex items-center gap-3">{stage.status === 'COMPLETED' ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" /> : stage.status === 'FAILED' ? <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" /> : ['RUNNING','RETRYING'].includes(stage.status) ? <Loader2 className="w-4 h-4 shrink-0 animate-spin text-blue-600" /> : <Circle className="w-4 h-4 shrink-0 text-stone-300" />}<span className="text-sm">{stageLabel(stage.stage_name)}</span></div><span className="text-[11px] font-semibold text-stone-500">{stage.status}</span></div>{stage.error_details && <p className="ml-7 text-xs text-rose-700 break-words">{stage.error_details}</p>}{stage.status !== 'PENDING' && <p className="ml-7 text-[10px] text-stone-400">{stage.responsible_worker} · {new Date(stage.updated_at).toLocaleTimeString()}</p>}</li>)}</ol>
        </section>
        <div className="space-y-6">
          <section className="bg-white border border-[#D1C2A5] rounded-2xl p-5 space-y-3"><h2 className="font-bold text-lg">Capture video</h2>{session.video_url && session.upload_verified_at ? <video key={session.video_url} controls preload="metadata" src={session.video_url} className="w-full max-h-80 bg-black rounded-xl" /> : <p className="text-sm text-stone-500">Playback becomes available after storage verification.</p>}
            {session.viewer_url && state?.tone === 'complete' && <a href={session.viewer_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 bg-emerald-700 text-white rounded-xl px-4 py-3 text-sm font-bold">Open completed 3D viewer<ExternalLink className="w-4 h-4" /></a>}
          </section>
          <section className="bg-[#211B16] text-stone-200 border border-stone-700 rounded-2xl overflow-hidden"><div className="px-5 py-4 border-b border-stone-700"><h2 className="font-bold">Worker execution log</h2><p className="text-xs text-stone-400 mt-1">Latest {logs.length} persisted messages from this job</p></div><div className="max-h-96 overflow-auto p-4 space-y-2 font-mono text-[11px] leading-relaxed" aria-live="off">{logs.length ? logs.map(log => <div key={log.id} className="whitespace-pre-wrap break-words"><span className="text-stone-500">{new Date(log.created_at).toLocaleTimeString()} </span><span className={log.log_level === 'error' ? 'text-rose-300' : ''}>{log.message}</span></div>) : <p className="text-stone-400">{session.job_id ? 'Waiting for the worker to write its first message.' : 'Execution logs will appear after processing is submitted.'}</p>}</div></section>
          <section className="bg-white border border-[#D1C2A5] rounded-2xl p-5 space-y-3"><h2 className="font-bold">Scan references</h2>{[['Capture',session.capture_id],['Upload',session.upload_id],['Processing job',session.job_id]].map(([label,value]) => <div key={label}><p className="text-xs text-stone-500">{label}</p><p className="font-mono text-[11px] break-all mt-1">{value || 'Not created yet'}</p></div>)}</section>
        </div>
      </div>
    </>}
  </div></main>;
};

function Metric({label,value,detail}: {label: string; value: string; detail: string}) {
  return <div className="bg-white border border-[#D1C2A5] rounded-xl p-5"><p className="text-xs uppercase tracking-wide text-stone-500">{label}</p><p className="text-lg font-bold mt-2">{value}</p><p className="text-xs text-stone-500 mt-1">{detail}</p></div>;
}
