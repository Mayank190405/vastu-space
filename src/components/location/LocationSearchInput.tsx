import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Crosshair, Loader2, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';
import { LocationSearchResult } from '../../types';

interface LocationSearchInputProps {
  address: {
    address_line_1: string;
    address_line_2?: string;
    area?: string;
    city: string;
    state: string;
    pincode: string;
    country: string;
    latitude?: number;
    longitude?: number;
    place_id?: string;
  };
  onChange: (updated: LocationSearchInputProps['address']) => void;
}

export const LocationSearchInput: React.FC<LocationSearchInputProps> = ({ address, onChange }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LocationSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounce search
  useEffect(() => {
    if (!query.trim() || query.length < 3) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const resp = await api.searchLocations(query, 6);
        setResults(resp.results || []);
        setShowDropdown(true);
      } catch (err) {
        console.error('Location search failed:', err);
      } finally {
        setIsSearching(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectResult = (r: LocationSearchResult) => {
    onChange({
      address_line_1: r.address_line_1 || r.display_name.split(',')[0],
      area: r.area || undefined,
      city: r.city || '',
      state: r.state || '',
      pincode: r.pincode || '',
      country: r.country || 'India',
      latitude: r.latitude,
      longitude: r.longitude,
      place_id: r.place_id,
    });
    setQuery(r.display_name);
    setShowDropdown(false);
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          const res = await api.reverseGeocode(lat, lng);
          onChange({
            address_line_1: res.address_line_1 || `Location at ${lat.toFixed(4)}, ${lng.toFixed(4)}`,
            area: res.area || undefined,
            city: res.city || '',
            state: res.state || '',
            pincode: res.pincode || '',
            country: res.country || 'India',
            latitude: lat,
            longitude: lng,
            place_id: res.place_id,
          });
          setQuery(res.display_name || `${lat.toFixed(5)}, ${lng.toFixed(5)}`);
        } catch (err) {
          console.error('Reverse geocode failed:', err);
          alert('Could not resolve address from GPS coordinates. Please enter manually.');
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        alert('Could not access current location: ' + err.message);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  return (
    <div className="space-y-4">
      {/* Search Bar with GPS Geolocation button */}
      <div className="relative" ref={dropdownRef}>
        <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
          Search Location / Landmark / Address
        </label>
        <div className="relative flex items-center">
          <Search className="w-5 h-5 text-[#8F6834] absolute left-3.5 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => {
              if (results.length > 0) setShowDropdown(true);
            }}
            placeholder="Search address, neighborhood, city, landmark..."
            className="w-full pl-11 pr-32 py-3 bg-[#FAF7F2] border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:ring-2 focus:ring-[#8F6834]/30 focus:border-[#8F6834] transition-all shadow-sm"
          />

          <div className="absolute right-2 flex items-center gap-1.5">
            {isSearching && <Loader2 className="w-4 h-4 text-[#8F6834] animate-spin mr-1" />}
            <button
              type="button"
              onClick={handleUseCurrentLocation}
              disabled={isLocating}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#FAF3E0] hover:bg-[#F3E7C4] text-[#8F6834] border border-[#D9C4A1] text-xs font-medium rounded-lg transition-colors shadow-xs"
              title="Detect Current Location via GPS"
            >
              {isLocating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Crosshair className="w-3.5 h-3.5" />
              )}
              <span>GPS</span>
            </button>
          </div>
        </div>

        {/* Autocomplete Dropdown */}
        {showDropdown && results.length > 0 && (
          <div className="absolute z-30 top-full left-0 right-0 mt-1.5 bg-[#FAF7F2] border border-[#D1C2A5] rounded-xl shadow-xl overflow-hidden max-h-60 overflow-y-auto divide-y divide-[#EAE2D3]">
            {results.map((r, idx) => (
              <button
                key={r.place_id || idx}
                type="button"
                onClick={() => handleSelectResult(r)}
                className="w-full text-left px-4 py-3 hover:bg-[#F3EDE2] transition-colors flex items-start gap-3 text-sm text-[#1F150D]"
              >
                <MapPin className="w-4 h-4 text-[#8F6834] shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{r.address_line_1 || r.display_name.split(',')[0]}</div>
                  <div className="text-xs text-[#7C6652] truncate">{r.display_name}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Structured Editable Fields */}
      <div className="p-4 bg-[#FAF7F2] rounded-xl border border-[#D1C2A5] space-y-3.5 shadow-xs">
        <div className="flex items-center justify-between border-b border-[#EAE2D3] pb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-[#8F6834]">
            Structured Project Address
          </span>
          {address.latitude && address.longitude && (
            <span className="text-[11px] font-mono bg-[#EFE7D8] text-[#5C4D3E] px-2 py-0.5 rounded-md border border-[#D9CEBC]">
              GPS: {address.latitude.toFixed(5)}, {address.longitude.toFixed(5)}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">
              Address Line 1 <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              required
              value={address.address_line_1}
              onChange={(e) => onChange({ ...address, address_line_1: e.target.value })}
              placeholder="Building No, Plot No, Street name"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">Address Line 2 (Optional)</label>
            <input
              type="text"
              value={address.address_line_2 || ''}
              onChange={(e) => onChange({ ...address, address_line_2: e.target.value })}
              placeholder="Suite, Floor, Wing, Landmark"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">Locality / Area</label>
            <input
              type="text"
              value={address.area || ''}
              onChange={(e) => onChange({ ...address, area: e.target.value })}
              placeholder="e.g. Indiranagar, Koramangala"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">
              City / District <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              required
              value={address.city}
              onChange={(e) => onChange({ ...address, city: e.target.value })}
              placeholder="e.g. Bengaluru"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">
              State <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              required
              value={address.state}
              onChange={(e) => onChange({ ...address, state: e.target.value })}
              placeholder="e.g. Karnataka"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">
              Postal Code / Pincode <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              required
              value={address.pincode}
              onChange={(e) => onChange({ ...address, pincode: e.target.value })}
              placeholder="e.g. 560038"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[#5C4D3E] mb-1">Country</label>
            <input
              type="text"
              value={address.country || 'India'}
              onChange={(e) => onChange({ ...address, country: e.target.value })}
              placeholder="India"
              className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-lg text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
