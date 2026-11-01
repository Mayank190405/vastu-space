import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import {
  Compass,
  Box,
  Layers,
  Sparkles,
  ArrowRight,
  Menu,
  X,
  ExternalLink,
  Shield,
  Activity,
  Code2,
  BookOpen,
  MapPin,
  CheckCircle2,
  ChevronRight
} from 'lucide-react';

interface WebsiteNavbarProps {
  activeSection?: string;
}

export const WebsiteNavbar: React.FC<WebsiteNavbarProps> = ({ activeSection }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [announcementDismissed, setAnnouncementDismissed] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'Overview', href: '#overview' },
    { label: 'Approach & Math', href: '#approach' },
    { label: '9-Stage Pipeline', href: '#pipeline' },
    { label: 'How to Use', href: '#how-to-use' },
    { label: 'SOP Simulator', href: '#sop-simulator' },
    { label: '3D Showcase', href: '#3d-showcase' },
    { label: 'Dadar Pilot Data', href: '#benchmarks' },
    { label: 'Vāstu Shastra', href: '#vastu-shastra' },
    { label: 'API & CLI', href: '#developer' },
    { label: 'FAQ', href: '#faq' },
  ];

  return (
    <>
      {/* Top Academic & Industrial Banner */}
      {!announcementDismissed && (
        <div className="bg-gradient-to-r from-[#211710] via-[#3A2A1A] to-[#211710] border-b border-[#C5A059]/30 text-xs py-2 px-4 text-[#F4ECE0] transition-all">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-2 overflow-hidden text-ellipsis whitespace-nowrap">
              <span className="px-2 py-0.5 rounded-full bg-[#C5A059]/20 text-[#E8C982] border border-[#C5A059]/40 font-mono text-[10px] uppercase tracking-wider font-semibold">
                Pilot Release
              </span>
              <span className="text-[#D8CDBA] text-xs">
                In Academic & Industrial Collaboration with <strong className="text-white font-medium">Create Fo'em Interior Designing Studio</strong> — Dadar West, Mumbai
              </span>
            </div>
            <div className="flex items-center space-x-4 shrink-0 pl-4">
              <a
                href="#benchmarks"
                className="hidden sm:inline-flex items-center text-[#E8C982] hover:text-white font-medium space-x-1 underline decoration-[#C5A059]/60 underline-offset-2 transition-colors"
              >
                <span>Ground-Truth Verification</span>
                <ChevronRight className="w-3 h-3" />
              </a>
              <button
                onClick={() => setAnnouncementDismissed(true)}
                className="text-[#9C9183] hover:text-white p-0.5 rounded transition-colors"
                aria-label="Dismiss banner"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Sticky Navbar */}
      <nav
        className={`sticky top-0 z-50 transition-all duration-300 ${
          scrolled
            ? 'bg-[#0E0C0A]/95 backdrop-blur-xl border-b border-[#C5A059]/30 shadow-2xl py-3'
            : 'bg-[#0E0C0A]/85 backdrop-blur-md border-b border-[#C5A059]/15 py-4'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          {/* Logo & Brand Identity */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-tr from-[#241A13] to-[#141210] border border-[#C5A059]/50 shadow-[0_0_15px_rgba(197,160,89,0.25)] group-hover:border-[#C5A059] transition-all">
              <img
                src="/vastu-brand.png"
                alt="VĀSTU Compass"
                className="w-7 h-7 object-contain filter drop-shadow-[0_2px_8px_rgba(197,160,89,0.4)] group-hover:rotate-12 transition-transform duration-500"
              />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center space-x-1.5">
                <span className="font-serif font-bold text-lg tracking-[0.18em] text-[#E8C982] group-hover:text-white transition-colors">
                  VĀSTU
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#C5A059]/20 text-[#C5A059] border border-[#C5A059]/40">
                  v3.0
                </span>
              </div>
              <span className="text-[10px] uppercase font-sans tracking-[0.2em] text-[#9C9183]">
                Namma Space · Spatial Computing
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <div className="hidden xl:flex items-center space-x-1 bg-[#141210]/60 border border-[#C5A059]/20 rounded-full px-3 py-1">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="px-3 py-1.5 rounded-full text-xs font-medium text-[#C4B9AC] hover:text-[#E8C982] hover:bg-[#C5A059]/10 transition-all"
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right Action CTA Buttons */}
          <div className="hidden md:flex items-center space-x-3">
            <Link
              to="/viewer"
              className="px-3.5 py-1.5 rounded-xl border border-[#C5A059]/40 bg-[#1A1714] text-[#E8C982] text-xs font-semibold hover:bg-[#26221D] hover:border-[#C5A059] transition-all flex items-center space-x-1.5 shadow-sm"
            >
              <Box className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>3D Twin Studio</span>
            </Link>

            <Link
              to="/ar"
              className="hidden lg:flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-emerald-400 text-xs font-semibold hover:bg-emerald-950/40 transition-all"
            >
              <Compass className="w-3.5 h-3.5 text-emerald-400" />
              <span>Live AR</span>
            </Link>

            {user ? (
              <Link
                to="/dashboard"
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C5A059] via-[#D9C099] to-[#C5A059] text-black text-xs font-bold hover:brightness-110 shadow-lg shadow-[#C5A059]/20 transition-all flex items-center space-x-1.5"
              >
                <span>Console Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <Link
                to="/login"
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C5A059] via-[#D9C099] to-[#C5A059] text-black text-xs font-bold hover:brightness-110 shadow-lg shadow-[#C5A059]/20 transition-all flex items-center space-x-1.5"
              >
                <span>Launch Console</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>

          {/* Mobile Hamburger Button */}
          <div className="flex md:hidden items-center space-x-2">
            <Link
              to={user ? '/dashboard' : '/login'}
              className="px-3 py-1.5 rounded-lg bg-[#C5A059] text-black text-xs font-bold"
            >
              Console
            </Link>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#0E0C0A] border-b border-[#C5A059]/30 px-6 py-6 space-y-4 shadow-2xl animate-in fade-in slide-in-from-top-2">
            <div className="grid grid-cols-2 gap-2 pb-4 border-b border-[#C5A059]/20">
              <Link
                to="/viewer"
                onClick={() => setMobileMenuOpen(false)}
                className="p-3 rounded-xl bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982] text-xs font-semibold flex items-center space-x-2"
              >
                <Box className="w-4 h-4 text-[#C5A059]" />
                <span>3D Studio</span>
              </Link>
              <Link
                to="/ar"
                onClick={() => setMobileMenuOpen(false)}
                className="p-3 rounded-xl bg-[#1A1714] border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center space-x-2"
              >
                <Compass className="w-4 h-4 text-emerald-400" />
                <span>Mobile AR</span>
              </Link>
            </div>

            <div className="flex flex-col space-y-2">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm text-[#C4B9AC] hover:text-[#E8C982] hover:bg-[#1A1714] font-medium transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>

            <div className="pt-4 border-t border-[#C5A059]/20 flex flex-col space-y-2">
              <Link
                to={user ? '/dashboard' : '/login'}
                onClick={() => setMobileMenuOpen(false)}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black text-center text-sm font-bold shadow-lg"
              >
                {user ? 'Enter Platform Dashboard' : 'Launch Console / Sign In'}
              </Link>
            </div>
          </div>
        )}
      </nav>
    </>
  );
};

