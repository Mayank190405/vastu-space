import React, { useState, useEffect } from 'react';
import { Smartphone, Battery, BatteryCharging, Wifi, Activity, Brain, Clock, RefreshCw, AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { api } from '../../services/api';
import { ConnectedDevice } from '../../types';

export const DeviceMonitoringPage: React.FC = () => {
  const [devices, setDevices] = useState<ConnectedDevice[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchDevices = async () => {
    try {
      const list = await api.listDevices();
      setDevices(list);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load connected devices:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderBatteryIcon = (level: number) => {
    if (level < 0) return <span className="text-gray-400">N/A</span>;
    const pct = Math.round(level * 100);
    return (
      <div className="flex items-center gap-1.5 text-xs font-mono font-medium">
        <Battery className={`w-4 h-4 ${pct <= 20 ? 'text-rose-500' : 'text-emerald-500'}`} />
        <span>{pct}%</span>
      </div>
    );
  };

  const getSecondsSince = (dateStr: string) => {
    const d = new Date(dateStr);
    const diffSec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
    return diffSec;
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1E293B] p-4 md:p-8 font-sans antialiased">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Connected Devices & Telemetry</h1>
            <p className="text-sm text-gray-500 mt-1">
              Real-time hardware status, ARKit visual-inertial tracking, and local AI model health for authorized capture devices
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">
              Synced {lastRefreshed.toLocaleTimeString()}
            </span>
            <button
              onClick={fetchDevices}
              className="p-2 bg-white rounded-xl border border-gray-200 text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors shadow-sm"
              title="Refresh device fleet"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Device Stats Summary Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Online Devices</p>
            <h3 className="text-2xl font-bold text-gray-900 mt-1">
              {devices.filter((d) => d.status === 'ONLINE').length}
            </h3>
            <p className="text-xs text-emerald-600 mt-1 flex items-center">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5" />
              Active heartbeats within 30s
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Registered</p>
            <h3 className="text-2xl font-bold text-gray-900 mt-1">{devices.length}</h3>
            <p className="text-xs text-gray-500 mt-1">Authorized iPhone fleet</p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">ARKit Tracking</p>
            <h3 className="text-2xl font-bold text-gray-900 mt-1">
              {devices.filter((d) => d.arkit_tracking_status === 'NORMAL').length} Normal
            </h3>
            <p className="text-xs text-gray-500 mt-1">Visual-inertial odometry stable</p>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">On-Device AI</p>
            <h3 className="text-2xl font-bold text-gray-900 mt-1">
              {devices.filter((d) => d.local_ai_status === 'READY').length} Ready
            </h3>
            <p className="text-xs text-emerald-600 mt-1">Core ML & Vision operational</p>
          </div>
        </div>

        {/* Device Listing */}
        {isLoading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading connected device telemetry...
          </div>
        ) : devices.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center space-y-3">
            <Smartphone className="w-10 h-10 text-gray-300 mx-auto" />
            <h3 className="text-base font-bold text-gray-900">No Devices Connected</h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              Devices register automatically when scanning a valid session QR code and report periodic heartbeats every 5–10 seconds.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {devices.map((device) => {
              const secSince = getSecondsSince(device.last_heartbeat_at);
              const isOnline = secSince <= 30;

              return (
                <div
                  key={device.device_uuid}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-5"
                >
                  {/* Top Bar: Device Model, UUID, Status Pill */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-700">
                        <Smartphone className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-gray-900">{device.device_model}</h3>
                        <p className="text-xs text-gray-400 font-mono">
                          UUID: {device.device_uuid.slice(0, 16)}... • {device.device_os}
                        </p>
                      </div>
                    </div>

                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                      isOnline ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-gray-100 text-gray-500'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`} />
                      {isOnline ? 'Online' : 'Offline'}
                    </span>
                  </div>

                  {/* Telemetry Metrics Grid */}
                  <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-100 text-xs">
                    <div>
                      <span className="text-gray-400 block font-medium">Battery Level</span>
                      <div className="mt-1">{renderBatteryIcon(device.battery_level)}</div>
                    </div>

                    <div>
                      <span className="text-gray-400 block font-medium">ARKit Tracking</span>
                      <div className="mt-1 font-semibold flex items-center">
                        <Activity className="w-3.5 h-3.5 mr-1 text-blue-500" />
                        <span className={device.arkit_tracking_status === 'NORMAL' ? 'text-gray-900' : 'text-amber-600'}>
                          {device.arkit_tracking_status}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-gray-400 block font-medium">Local Core ML Status</span>
                      <div className="mt-1 font-semibold flex items-center text-gray-900">
                        <Brain className="w-3.5 h-3.5 mr-1 text-purple-500" />
                        {device.local_ai_status}
                      </div>
                    </div>

                    <div>
                      <span className="text-gray-400 block font-medium">Network Type</span>
                      <div className="mt-1 font-semibold flex items-center text-gray-900">
                        <Wifi className="w-3.5 h-3.5 mr-1 text-gray-500" />
                        {device.network_type}
                      </div>
                    </div>
                  </div>

                  {/* Current Active Session */}
                  <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                    <span className="text-gray-500">
                      Active Session: <span className="font-mono font-semibold text-gray-800">{device.current_session_id || 'None'}</span>
                    </span>
                    <span className="text-gray-400 flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1 text-gray-400" />
                      {secSince < 60 ? `${secSince}s ago` : `${Math.floor(secSince / 60)}m ago`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
};

