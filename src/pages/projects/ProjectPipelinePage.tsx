import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Activity } from 'lucide-react';
import { useProjectPipelines } from '../../hooks/useProjectPipelines';
import { ProjectPipelinePanel } from '../../components/pipeline/ProjectPipelinePanel';
import { isSubmitted, pipelineState } from '../../components/pipeline/pipelineState';

export const ProjectPipelinePage: React.FC = () => {
  const { projectId } = useParams<{projectId: string}>();
  const data = useProjectPipelines(projectId);
  const submitted = data.entries.filter(e => isSubmitted(e.session));
  const counts = [
    ['Submitted scans', submitted.length],
    ['In progress', submitted.filter(e => ['running','queued','retrying'].includes(pipelineState(e).tone)).length],
    ['Need attention', submitted.filter(e => pipelineState(e).tone === 'failed').length],
    ['Viewer ready', submitted.filter(e => pipelineState(e).tone === 'complete').length],
  ];
  return <main className="min-h-screen bg-[#FAF7F2] p-4 md:p-8 text-[#1F150D]"><div className="max-w-6xl mx-auto space-y-6">
    <Link to={`/projects/${projectId}`} className="inline-flex gap-2 items-center text-sm text-[#695541]"><ArrowLeft className="w-4 h-4" />Back to project</Link>
    <header><p className="text-xs uppercase tracking-widest text-[#8F6834] mb-2">{data.entries[0]?.session.project_name || 'Project'}</p><h1 className="text-3xl font-bold flex gap-3 items-center"><Activity className="text-[#8F6834]" />Scan pipeline dashboard</h1><p className="text-sm text-[#695541] mt-2">Follow every submitted scan from video upload through reconstruction and viewer publishing.</p></header>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{counts.map(([label,value]) => <div key={label} className="bg-white border border-[#D1C2A5] rounded-xl p-5"><p className="text-xs text-stone-500">{label}</p><p className="text-3xl font-semibold mt-2">{value}</p></div>)}</div>
    <ProjectPipelinePanel projectId={projectId!} {...data} />
  </div></main>;
};
