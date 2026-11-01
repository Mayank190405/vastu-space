import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, QrCode, Search, Smartphone, Clock, Play, ArrowRight, ShieldCheck, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { CaptureSessionRecord, Project } from '../../types';

export const SessionListPage: React.FC = () => {
  const [sessions, setSessions] = useState<CaptureSessionRecord[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);

  // New session modal form state
  const [newSessionRoomName, setNewSessionRoomName] = useState<string>('');
  const [newSessionProject, setNewSessionProject] = useState<string>('');
  const [newSessionTTL, setNewSessionTTL] = useState<number>(60);
  const [isCreating, setIsCreating] = useState<boolean>(false);

  const fetchSessions = async () => {
    try {
      setIsLoading(true);
      const [sessionsData, projectsData] = await Promise.all([
        api.listQRSessions(selectedProjectId || undefined).catch(() => []),
        api.listProjects().catch(() => []),
      ]);
      setSessions(sessionsData);
      setProjects(projectsData);
      if (projectsData.length > 0 && !newSessionProject) {
        setNewSessionProject(projectsData[0].id);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [selectedProjectId]);

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSessionProject || !newSessionRoomName.trim()) {
      alert('Please specify a project and room name');
      return;
    }
    try {
      setIsCreating(true);
      const created = await api.createQRSession({
        project_id: newSessionProject,
        room_name: newSessionRoomName.trim(),
        ttl_minutes: newSessionTTL,
      });
      setShowCreateModal(false);
      setNewSessionRoomName('');
      await fetchSessions();
    } catch (err: any) {
      alert(err.message || 'Failed to create capture session');
    } finally {
      setIsCreating(false);
    }
  };

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch = s.room_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.session_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.project_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1E293B] p-4 md:p-8 font-sans antialiased">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Capture Sessions & QR Manager</h1>
            <p className="text-sm text-gray-500 mt-1">
              Create, authorize, and track QR recording sessions across all projects and devices
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              New QR Session
            </button>
          </div>
        </div>

        {/* Filters Bar */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by room, session #, or project..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-gray-50 rounded-xl border-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="px-3 py-2 text-sm bg-gray-50 rounded-xl border-none text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            <button
              onClick={fetchSessions}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-xl hover:bg-gray-100 transition-colors"
              title="Refresh sessions"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Sessions Grid / Table */}
        {isLoading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading capture sessions...
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center space-y-3">
            <QrCode className="w-10 h-10 text-gray-300 mx-auto" />
            <h3 className="text-base font-bold text-gray-900">No Capture Sessions Found</h3>
            <p className="text-sm text-gray-500">
              Create a new QR session to allow an authorized iPhone to start scanning a room.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-2 px-4 py-2 bg-gray-900 text-white rounded-xl text-xs font-semibold hover:bg-gray-800"
            >
              Create Session
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-gray-50/50">
                    <th className="px-6 py-4">Session</th>
                    <th className="px-6 py-4">Room & Project</th>
                    <th className="px-6 py-4">Device</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Expires</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredSessions.map((s) => (
                    <tr key={s.id} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-gray-900">
                        {s.session_code}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-semibold text-gray-900">{s.room_name}</div>
                        <div className="text-xs text-gray-500">{s.project_name}</div>
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-xs">
                        {s.device_id ? (
                          <span className="flex items-center text-gray-800 font-medium">
                            <Smartphone className="w-3.5 h-3.5 mr-1 text-gray-400" />
                            {s.device_id.slice(0, 10)}
                          </span>
                        ) : (
                          <span className="text-gray-400">Waiting for scan</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          s.status === 'AUTHORIZED' || s.status === 'RECORDING' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                          s.status === 'COMPLETED' ? 'bg-blue-50 text-blue-600 border border-blue-100' :
                          s.status === 'EXPIRED' || s.status === 'REVOKED' ? 'bg-rose-50 text-rose-600 border border-rose-100' :
                          'bg-amber-50 text-amber-600 border border-amber-100'
                        }`}>
                          {s.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-gray-500">
                        {new Date(s.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        <Link
                          to={`/dashboard/sessions/${s.id}`}
                          className="inline-flex items-center px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium transition-colors"
                        >
                          <QrCode className="w-3.5 h-3.5 mr-1" />
                          View QR
                        </Link>
                        <Link
                          to={`/dashboard/reconstruction/${s.id}`}
                          className="inline-flex items-center px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg text-xs font-medium transition-colors"
                        >
                          <Play className="w-3.5 h-3.5 mr-1" />
                          Pipeline
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

      {/* Create Session Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-xl max-w-md w-full p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Create Recording Session QR</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-gray-600 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                  Select Project
                </label>
                <select
                  value={newSessionProject}
                  onChange={(e) => setNewSessionProject(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                  Room or Space Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Master Bedroom, Living Room Suite"
                  value={newSessionRoomName}
                  onChange={(e) => setNewSessionRoomName(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                  QR Session Validity (Minutes)
                </label>
                <input
                  type="number"
                  min="15"
                  max="1440"
                  value={newSessionTTL}
                  onChange={(e) => setNewSessionTTL(Number(e.target.value))}
                  className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-4 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl shadow-sm"
                >
                  {isCreating ? 'Generating QR...' : 'Generate Session QR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

