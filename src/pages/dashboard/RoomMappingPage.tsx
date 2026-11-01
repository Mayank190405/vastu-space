import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Layers, Plus, QrCode, Play, RotateCcw, Box, CheckCircle2, AlertTriangle, ArrowLeft, RefreshCw, Eye, ExternalLink } from 'lucide-react';
import { api } from '../../services/api';
import { RoomWithHierarchy, Project, ProjectFloor } from '../../types';

export const RoomMappingPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  const [project, setProject] = useState<Project | null>(null);
  const [floors, setFloors] = useState<ProjectFloor[]>([]);
  const [rooms, setRooms] = useState<RoomWithHierarchy[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showAddRoomModal, setShowAddRoomModal] = useState<boolean>(false);
  const [selectedFloorId, setSelectedFloorId] = useState<string>('');

  // Form states
  const [newRoomName, setNewRoomName] = useState<string>('');
  const [newRoomType, setNewRoomType] = useState<string>('room');
  const [newRoomArea, setNewRoomArea] = useState<number>(20);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchData = async () => {
    if (!projectId) return;
    try {
      setIsLoading(true);
      const [projData, floorsData, roomsData] = await Promise.all([
        api.getProject(projectId).catch(() => null),
        api.listFloors(projectId).catch(() => []),
        api.listRoomsByProject(projectId).catch(() => []),
      ]);
      setProject(projData);
      setFloors(floorsData);
      setRooms(roomsData);
      if (floorsData.length > 0 && !selectedFloorId) {
        setSelectedFloorId(floorsData[0].id);
      }
    } catch (err) {
      console.error('Failed to load room mapping data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [projectId]);

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !selectedFloorId || !newRoomName.trim()) return;

    try {
      setIsSubmitting(true);
      await api.createRoom(projectId, selectedFloorId, {
        name: newRoomName.trim(),
        section_type: newRoomType,
        area_sqm: newRoomArea,
      });
      setShowAddRoomModal(false);
      setNewRoomName('');
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to create room');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestRescan = async (roomId: string, roomName: string) => {
    if (!projectId) return;
    try {
      const created = await api.createQRSession({
        project_id: projectId,
        room_id: roomId,
        room_name: `${roomName} (Rescan)`,
        ttl_minutes: 120,
      });
      alert(`Rescan session created with code ${created.session_code}! Scan the new QR code to rescan without overwriting previous data.`);
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to initiate rescan session');
    }
  };

  // Group rooms by floor
  const floorMap = new Map<string, { floorName: string; levelNumber: number; rooms: RoomWithHierarchy[] }>();
  for (const r of rooms) {
    const key = r.level_id || 'default_floor';
    if (!floorMap.has(key)) {
      floorMap.set(key, {
        floorName: r.level_name || 'Floor 1',
        levelNumber: r.level_number || 1,
        rooms: [],
      });
    }
    floorMap.get(key)!.rooms.push(r);
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1E293B] p-4 md:p-8 font-sans antialiased">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Back Link */}
        <Link
          to={`/projects/${projectId}`}
          className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Project Overview
        </Link>

        {/* Top Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">
              {project?.name || 'Project'} — Room Mapping Dashboard
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Floor-wise room management, capture sessions, provisional floorplans, and reconstruction states
            </p>
          </div>

          <button
            onClick={() => setShowAddRoomModal(true)}
            className="inline-flex items-center px-4 py-2 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Add Room to Floor
          </button>
        </div>

        {/* Room Hierarchy by Floor */}
        {isLoading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading project rooms & floors...
          </div>
        ) : floorMap.size === 0 && rooms.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center space-y-3">
            <Layers className="w-10 h-10 text-gray-300 mx-auto" />
            <h3 className="text-base font-bold text-gray-900">No Rooms Defined</h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              Add rooms to floors in this project to generate session QR codes and begin scanning with the mobile app.
            </p>
            <button
              onClick={() => setShowAddRoomModal(true)}
              className="mt-2 px-4 py-2 bg-gray-900 text-white rounded-xl text-xs font-semibold hover:bg-gray-800"
            >
              Add First Room
            </button>
          </div>
        ) : (
          <div className="space-y-8">
            {Array.from(floorMap.entries()).map(([floorKey, floorGroup]) => (
              <div key={floorKey} className="space-y-4">
                
                {/* Floor Header */}
                <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                  <div className="flex items-center space-x-2">
                    <Layers className="w-5 h-5 text-gray-500" />
                    <h2 className="text-lg font-bold text-gray-900">{floorGroup.floorName}</h2>
                    <span className="text-xs text-gray-400 font-mono">({floorGroup.rooms.length} rooms)</span>
                  </div>
                </div>

                {/* Rooms Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {floorGroup.rooms.map((room) => {
                    const hasDims = room.dimensions_validated && room.dimensions_validated.length_m;
                    const isReconstructed = room.capture_status === 'RECONSTRUCTED';

                    return (
                      <div
                        key={room.id}
                        className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-4 flex flex-col justify-between"
                      >
                        <div className="space-y-3">
                          {/* Top Row: Room Name & Status */}
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="font-bold text-gray-900 text-base">{room.name}</h3>
                              <p className="text-xs text-gray-400 capitalize">{room.section_type} • {room.area_sqm} m²</p>
                            </div>

                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              room.capture_status === 'RECONSTRUCTED' ? 'bg-blue-50 text-blue-600 border border-blue-100' :
                              room.capture_status === 'CAPTURED' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                              room.capture_status === 'CAPTURING' ? 'bg-purple-50 text-purple-600 border border-purple-100' :
                              'bg-gray-100 text-gray-500'
                            }`}>
                              {room.capture_status}
                            </span>
                          </div>

                          {/* Dimensions & Quality Metrics */}
                          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-gray-100 text-gray-600">
                            <div>
                              <span className="text-gray-400 block font-medium">Coverage</span>
                              <span className="font-semibold text-gray-900">{Math.round(room.coverage_percentage)}%</span>
                            </div>
                            <div>
                              <span className="text-gray-400 block font-medium">Quality Score</span>
                              <span className="font-semibold text-gray-900">{Math.round(room.quality_score)}%</span>
                            </div>

                            {hasDims && (
                              <div className="col-span-2 text-[11px] font-mono text-gray-700 bg-gray-50 p-1.5 rounded-lg mt-1">
                                {room.dimensions_validated?.length_m}m × {room.dimensions_validated?.width_m}m × {room.dimensions_validated?.height_m}m
                              </div>
                            )}
                          </div>

                          {/* Provisional Floorplan Thumbnail Preview */}
                          {room.provisional_floorplan_url && (
                            <div className="h-28 bg-gray-50 rounded-xl border border-gray-100 overflow-hidden relative group">
                              <img
                                src={room.provisional_floorplan_url}
                                alt="Provisional Floorplan"
                                className="w-full h-full object-contain p-2"
                              />
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-medium">
                                Preview Provisional Floorplan
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Actions Toolbar */}
                        <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs gap-2">
                          {room.active_session_id ? (
                            <Link
                              to={`/dashboard/reconstruction/${room.active_session_id}`}
                              className="inline-flex items-center text-blue-600 hover:text-blue-800 font-semibold"
                            >
                              <Play className="w-3.5 h-3.5 mr-1" />
                              View Pipeline ({room.active_session_code})
                            </Link>
                          ) : (
                            <button
                              onClick={() => handleRequestRescan(room.id, room.name)}
                              className="inline-flex items-center text-gray-700 hover:text-gray-900 font-medium"
                            >
                              <QrCode className="w-3.5 h-3.5 mr-1" />
                              Generate QR
                            </button>
                          )}

                          <button
                            onClick={() => handleRequestRescan(room.id, room.name)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                            title="Create new rescan session"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>

                          {isReconstructed && (
                            <Link
                              to={`/projects/${projectId}/viewer`}
                              className="inline-flex items-center px-2 py-1 bg-gray-900 text-white rounded-lg text-xs font-semibold hover:bg-gray-800"
                            >
                              <Eye className="w-3 h-3 mr-1" />
                              3D View
                            </Link>
                          )}
                        </div>

                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>

      {/* Add Room Modal */}
      {showAddRoomModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-xl max-w-md w-full p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Add Room to Floor</h3>
              <button onClick={() => setShowAddRoomModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <form onSubmit={handleCreateRoom} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                  Select Target Floor
                </label>
                <select
                  value={selectedFloorId}
                  onChange={(e) => setSelectedFloorId(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {floors.map((fl) => (
                    <option key={fl.id} value={fl.id}>{fl.name || `Floor ${fl.floor_number}`}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                  Room Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Master Bedroom, Dining Hall"
                  value={newRoomName}
                  onChange={(e) => setNewRoomName(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                    Room Type
                  </label>
                  <select
                    value={newRoomType}
                    onChange={(e) => setNewRoomType(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="room">Room</option>
                    <option value="hall">Hall / Living</option>
                    <option value="corridor">Corridor / Foyer</option>
                    <option value="kitchen">Kitchen</option>
                    <option value="balcony">Balcony</option>
                    <option value="bathroom">Bathroom</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1.5">
                    Est. Area (m²)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="1000"
                    value={newRoomArea}
                    onChange={(e) => setNewRoomArea(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm bg-gray-50 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddRoomModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-xl shadow-sm"
                >
                  {isSubmitting ? 'Saving...' : 'Add Room'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
