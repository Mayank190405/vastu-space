import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { ScanPipeline, isSubmitted, terminalPipeline } from '../components/pipeline/pipelineState';

export function useProjectPipelines(projectId?: string) {
  const [entries, setEntries] = useState<ScanPipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [revision, setRevision] = useState(0);
  const cache = useRef<ScanPipeline[]>([]);
  const refresh = useCallback(() => setRevision(n => n + 1), []);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    if (!projectId) return;
    setLoading(true);
    setError(null);
    cache.current = [];
    if (revision === 0) setEntries([]);
    const poll = async () => {
      try {
        if (document.visibilityState === 'hidden') { timer = setTimeout(poll, 5000); return; }
        const sessions = await api.listQRSessions(projectId);
        const scans = await Promise.all((sessions || []).map(async session => {
          const previous = cache.current.find(e => e.session.id === session.id);
          if (!isSubmitted(session)) return { session, stages: [] } as ScanPipeline;
          if (previous && previous.session.job_id === session.job_id && terminalPipeline(previous)) return { ...previous, session };
          const [stages, job] = await Promise.all([
            api.getPipelineStages(session.id), session.job_id ? api.getJob(session.job_id) : Promise.resolve(undefined),
          ]);
          return { session, stages: stages || [], job } as ScanPipeline;
        }));
        if (!active) return;
        cache.current = scans;
        setEntries(scans);
        setUpdatedAt(new Date());
        setError(null);
        // Keep discovering new mobile submissions; terminal jobs themselves are cached.
        timer = setTimeout(poll, 5000);
      } catch (err: any) {
        if (active) setError(err.message || 'Pipeline status unavailable. Refresh to retry.');
      } finally { if (active) setLoading(false); }
    };
    poll();
    return () => { active = false; clearTimeout(timer); };
  }, [projectId, revision]);
  return { entries, loading, error, updatedAt, refresh };
}
