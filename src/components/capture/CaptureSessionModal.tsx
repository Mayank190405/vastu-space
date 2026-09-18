import React, { useState } from 'react';
import {
  Camera,
  Layers,
  User,
  X,
  Sparkles,
  ChevronRight,
  ShieldCheck,
  Share2,
  Copy,
  Check,
  Info
} from 'lucide-react';
import { Project, ProjectFloor, ProjectMember } from '../../types';

interface CaptureSessionModalProps {
  project: Project;
  currentUserId?: string;
  onClose: () => void;
  onLaunchSession: (sessionData: {
    floorId: string;
    operatorId: string;
    operatorName: string;
    operatorType: 'SELF' | 'ASSIGNED';
    notes: string;
  }) => void;
}

export const CaptureSessionModal: React.FC<CaptureSessionModalProps> = ({
  project,
  currentUserId,
  onClose,
  onLaunchSession
}) => {
  const floors = project.floors || [];
  const team = project.team || [];

  const [selectedFloorId, setSelectedFloorId] = useState<string>(
    floors.length > 0 ? floors[0].id : ''
  );
  const [assignmentType, setAssignmentType] = useState<'SELF' | 'ASSIGNED'>('SELF');
  const [assignedUserId, setAssignedUserId] = useState<string>(
    team.length > 0 ? team[0].user_id : ''
  );
  const [notes, setNotes] = useState('');
  const [copiedLink, setCopiedLink] = useState(false);

  const selectedFloor = floors.find((f) => f.id === selectedFloorId);
  const assignedMember = team.find((m) => m.user_id === assignedUserId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFloorId) {
      alert('Please select a target floor level for capture.');
      return;
    }

    const opId = assignmentType === 'SELF' ? (currentUserId || 'self') : assignedUserId;
    const opName =
      assignmentType === 'SELF'
        ? 'Project Admin (Self)'
        : assignedMember?.user?.full_name || 'Assigned Surveyor';

    onLaunchSession({
      floorId: selectedFloorId,
      operatorId: opId,
      operatorName: opName,
      operatorType: assignmentType,
      notes
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-[#FAF7F2] border border-[#D1C2A5] rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-6 bg-white border-b border-[#EAE2D3] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#FAF3E0] text-[#8F6834] flex items-center justify-center">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#1F150D] font-serif-brand">
                Create Spatial Capture Session
              </h2>
              <p className="text-xs text-[#695541]">
                {project.name} &bull; 25-Stage Standardized Evidence Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-[#7C6652] hover:text-[#1F150D] hover:bg-[#FAF7F2] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* 1. Target Floor / Level Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-[#1F150D] flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-[#8F6834]" />
              <span>Target Level & Floor Plan</span>
            </label>
            {floors.length === 0 ? (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
                No floors found. Default Ground Level will be initialized.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {floors.map((floor) => {
                  const selected = selectedFloorId === floor.id;
                  return (
                    <div
                      key={floor.id}
                      onClick={() => setSelectedFloorId(floor.id)}
                      className={`p-3 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between ${
                        selected
                          ? 'bg-[#8F6834]/10 border-[#8F6834] ring-1 ring-[#8F6834]'
                          : 'bg-white border-[#EAE2D3] hover:border-[#D1C2A5]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-[#1F150D]">{floor.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#FAF7F2] text-[#8F6834]">
                          Lvl #{floor.floor_number}
                        </span>
                      </div>
                      <div className="text-[11px] text-[#7C6652] mt-1 flex items-center justify-between">
                        <span>{floor.floor_type}</span>
                        <span>{floor.area_value} {floor.area_unit}</span>
                      </div>
                      <div className="text-[10px] text-emerald-600 font-semibold mt-1 flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        <span>{floor.floor_plan ? 'Architectural Plan Linked' : 'Vector Grid Ready'}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. Operator Assignment: Self vs Surveyor */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-[#1F150D] flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-[#8F6834]" />
              <span>Surveyor Operator Assignment</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAssignmentType('SELF')}
                className={`p-3.5 rounded-2xl border text-left transition-all ${
                  assignmentType === 'SELF'
                    ? 'bg-[#8F6834] text-white border-[#8F6834] shadow-sm'
                    : 'bg-white text-[#1F150D] border-[#EAE2D3] hover:bg-[#FAF7F2]'
                }`}
              >
                <div className="font-bold text-xs">Capture Myself</div>
                <div className={`text-[11px] mt-0.5 ${assignmentType === 'SELF' ? 'text-white/80' : 'text-[#7C6652]'}`}>
                  Launch studio immediately on this device
                </div>
              </button>

              <button
                type="button"
                onClick={() => setAssignmentType('ASSIGNED')}
                className={`p-3.5 rounded-2xl border text-left transition-all ${
                  assignmentType === 'ASSIGNED'
                    ? 'bg-[#8F6834] text-white border-[#8F6834] shadow-sm'
                    : 'bg-white text-[#1F150D] border-[#EAE2D3] hover:bg-[#FAF7F2]'
                }`}
              >
                <div className="font-bold text-xs">Assign Team Surveyor</div>
                <div className={`text-[11px] mt-0.5 ${assignmentType === 'ASSIGNED' ? 'text-white/80' : 'text-[#7C6652]'}`}>
                  Delegate to onsite surveyor with mobile link
                </div>
              </button>
            </div>

            {assignmentType === 'ASSIGNED' && (
              <div className="mt-2 p-3 bg-white rounded-xl border border-[#EAE2D3] space-y-2">
                <label className="text-[11px] font-bold text-[#5C4D3E]">Select Team Member</label>
                {team.length === 0 ? (
                  <p className="text-xs text-amber-700">No team members assigned to project yet.</p>
                ) : (
                  <select
                    value={assignedUserId}
                    onChange={(e) => setAssignedUserId(e.target.value)}
                    className="w-full p-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] focus:outline-none focus:ring-2 focus:ring-[#8F6834]"
                  >
                    {team.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.user?.full_name || m.user?.email} ({m.project_role})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>

          {/* 3. Session Notes & Instructions */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-[#1F150D]">
              Surveyor Instructions & Special Focus (Optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Focus on corner column clearances, ensure doors stay open during walkaround..."
              className="w-full p-3 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:ring-2 focus:ring-[#8F6834]"
            />
          </div>

          {/* Spatial SOP Notice */}
          <div className="p-3.5 bg-[#FAF3E0] border border-[#D9C4A1] rounded-2xl flex items-start gap-2.5">
            <Sparkles className="w-4 h-4 text-[#8F6834] shrink-0 mt-0.5" />
            <div className="text-xs text-[#5C4D3E]">
              <span className="font-bold text-[#1F150D]">Spatial Capture Protocol: </span>
              The surveyor will first complete a 360° reconnaissance scan of the whole place. The system will analyze the floor plan and video to generate space-specific guidelines and mistake warnings before final area recording begins.
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#EAE2D3]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#7C6652] hover:text-[#1F150D]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all"
            >
              <span>Launch Guided Capture Studio</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
