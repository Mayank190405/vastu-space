import React from 'react';
import { Home, Layers, Check, ChevronDown } from 'lucide-react';

interface RoomItem {
  room_id: string;
  room_name: string;
  floor_level: number;
  area_sqm: number;
}

interface RoomSelectorProps {
  rooms: RoomItem[];
  selectedRoomId: string;
  onSelectRoom: (roomId: string) => void;
  onEnterWalkMode?: (roomId: string) => void;
}

export const RoomSelector: React.FC<RoomSelectorProps> = ({
  rooms,
  selectedRoomId,
  onSelectRoom,
  onEnterWalkMode,
}) => {
  const [isOpen, setIsOpen] = React.useState(false);

  const selectedRoom = rooms.find((r) => r.room_id === selectedRoomId) || rooms[0];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-slate-900/85 backdrop-blur-md border border-slate-700/80 text-white text-xs font-semibold shadow-xl hover:bg-slate-800 transition"
      >
        <Home className="w-4 h-4 text-[#C5A059]" />
        <span>{selectedRoom ? selectedRoom.room_name : 'Select Room'}</span>
        <span className="text-[10px] text-slate-400 font-normal">
          ({selectedRoom ? `${selectedRoom.area_sqm.toFixed(1)} m²` : ''})
        </span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 left-0 w-64 bg-slate-900/95 backdrop-blur-lg border border-slate-700 rounded-xl shadow-2xl p-2 z-50 text-xs">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1 mb-1">
            Connected Rooms
          </div>
          <div className="space-y-1 max-h-56 overflow-y-auto">
            {rooms.map((room) => {
              const isSelected = room.room_id === selectedRoomId;
              return (
                <div
                  key={room.room_id}
                  className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${
                    isSelected
                      ? 'bg-[#C5A059]/20 text-[#C5A059] border border-[#C5A059]/40'
                      : 'text-slate-200 hover:bg-slate-800'
                  }`}
                  onClick={() => {
                    onSelectRoom(room.room_id);
                    setIsOpen(false);
                  }}
                >
                  <div>
                    <div className="font-semibold">{room.room_name}</div>
                    <div className="text-[10px] text-slate-400">
                      Floor {room.floor_level} • {room.area_sqm.toFixed(1)} m²
                    </div>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-[#C5A059]" />}
                </div>
              );
            })}
          </div>

          {onEnterWalkMode && selectedRoom && (
            <div className="pt-2 border-t border-slate-700 mt-2">
              <button
                onClick={() => {
                  onEnterWalkMode(selectedRoom.room_id);
                  setIsOpen(false);
                }}
                className="w-full py-2 bg-[#C5A059] hover:bg-[#b08b47] text-slate-950 font-bold rounded-lg transition text-center"
              >
                Enter Walk Mode Here
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

