import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { BrandLogo } from '../../components/brand/BrandLogo';
import { triggerGoogleSignIn } from '../../services/googleAuth';
import {
  Mail,
  KeyRound,
  Lock,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  AlertCircle,
  Building,
  Building2,
  CheckCircle2,
  UserPlus,
  Users,
  Compass,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, setSession, hasActiveOrg, hasPendingJoin, isLoading: authLoading } = useAuth();

  const searchParams = new URLSearchParams(location.search);
  const redirectTarget = searchParams.get('redirect');

  const initialTab = location.pathname.includes('/register')
    ? 'register'
    : location.pathname.includes('/join')
    ? 'join'
    : 'signin';

  const [primaryTab, setPrimaryTab] = useState<'signin' | 'register' | 'join'>(initialTab);
  const [authMethod, setAuthMethod] = useState<'otp' | 'password'>('otp');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [joinOrgCode, setJoinOrgCode] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // If user already has an active session, automatically redirect them without showing the login screen
  useEffect(() => {
    if (!authLoading && user) {
      if (hasActiveOrg) {
        navigate(redirectTarget || '/dashboard', { replace: true });
      } else if (hasPendingJoin) {
        navigate('/pending-approval', { replace: true });
      } else {
        navigate('/signup/organization', { replace: true });
      }
    }
  }, [user, hasActiveOrg, hasPendingJoin, authLoading, navigate, redirectTarget]);

  const resolvePostLoginRedirect = (memberships?: any[]) => {
    const activeMembership = memberships?.find((m: any) => m.status === 'active');
    if (activeMembership) {
      navigate(redirectTarget || '/dashboard', { replace: true });
    } else if (memberships?.some((m: any) => m.status === 'invited')) {
      navigate('/pending-approval', { replace: true });
    } else {
      navigate('/signup/organization', { replace: true });
    }
  };

  const extractActiveOrg = (membership?: any): any => {
    if (!membership) return undefined;
    if (membership.organization) return membership.organization;
    if (membership.org_id) {
      return {
        id: membership.org_id,
        name: membership.org_name || 'Workspace',
        org_code: membership.org_code || '',
        status: 'active',
        created_at: membership.created_at || new Date().toISOString(),
      };
    }
    return undefined;
  };

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter a valid email address');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.sendOTP(email, 'LOGIN');
      setOtpSent(true);
      setOtpCode('');
      if (res?.debug_otp) {
        setSuccessMsg(`Verification code sent to ${email} (Dev Code: ${res.debug_otp})`);
      } else {
        setSuccessMsg(`Verification code sent to ${email}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send OTP. Please verify email address.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode || otpCode.length < 6) {
      setError('Please enter the 6-digit verification code');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.verifyOTP(email, otpCode, 'LOGIN');
      if (res.user && (res.tokens || res.token)) {
        const activeMembership = res.memberships?.find((m) => m.status === 'active');
        setSession({
          user: res.user,
          tokens: res.tokens,
          token: res.token,
          activeOrg: extractActiveOrg(activeMembership),
          activeRole: activeMembership?.role,
          memberships: res.memberships,
        });

        resolvePostLoginRedirect(res.memberships);
      } else {
        setError('No account found with this email. Please sign up or register an organization.');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid or expired OTP code');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      const activeMembership = res.memberships?.find((m) => m.status === 'active');
      setSession({
        user: res.user,
        tokens: res.tokens,
        token: res.token,
        activeOrg: extractActiveOrg(activeMembership),
        activeRole: activeMembership?.role,
        memberships: res.memberships,
      });

      resolvePostLoginRedirect(res.memberships);
    } catch (err: any) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const idToken = await triggerGoogleSignIn();
      const res = await api.googleAuth(idToken);
      const activeMembership = res.memberships?.find((m) => m.status === 'active');
      setSession({
        user: res.user,
        tokens: res.tokens,
        token: res.token,
        activeOrg: extractActiveOrg(activeMembership),
        activeRole: activeMembership?.role,
        memberships: res.memberships,
      });
      resolvePostLoginRedirect(res.memberships);
    } catch (err: any) {
      setError('Google Sign-In: ' + (err.message || 'Please use Email OTP or Password'));
    } finally {
      setIsLoading(false);
    }
  };

  const inputStyle =
    'input-brand w-full pl-9 pr-4 py-2.5 bg-white border border-[#C5A059]/40 hover:border-[#C5A059]/70 rounded-xl text-[#241A12] font-medium text-sm focus:outline-none focus:ring-2 focus:ring-[#C5A059]/30 focus:border-[#9E742A] placeholder-[#9C8E7E] shadow-sm transition-all';

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Brand Warm Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[320px] bg-[#C5A059]/15 blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 left-10 w-[300px] h-[300px] bg-[#B08940]/10 blur-[100px] rounded-full pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="flex justify-center items-center mb-3">
          <BrandLogo size="lg" showTagline theme="light" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-[#241A12] font-serif-brand">
          Spatial Cloud Authentication
        </h2>
        <p className="mt-1 text-xs text-[#5C4A38] font-medium">
          Multi-tenant spatial platform for architecture studios & teams
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4">
        <div className="glass-panel py-8 px-6 sm:px-8 rounded-2xl shadow-2xl border border-[#C5A059]/35">
          {/* Primary Top Tab Switcher */}
          <div className="flex rounded-xl bg-[#E8DEC9]/80 p-1 mb-6 border border-[#C5A059]/30 shadow-inner">
            <button
              type="button"
              onClick={() => {
                setPrimaryTab('signin');
                setError(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
                primaryTab === 'signin'
                  ? 'bg-white text-[#241A12] shadow-sm border border-[#C5A059]/30'
                  : 'text-[#6E5945] hover:text-[#241A12]'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5 text-[#9E742A]" />
              <span>Sign In</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setPrimaryTab('register');
                setError(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
                primaryTab === 'register'
                  ? 'bg-white text-[#241A12] shadow-sm border border-[#C5A059]/30'
                  : 'text-[#6E5945] hover:text-[#241A12]'
              }`}
            >
              <UserPlus className="w-3.5 h-3.5 text-[#9E742A]" />
              <span>Register</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setPrimaryTab('join');
                setError(null);
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
                primaryTab === 'join'
                  ? 'bg-white text-[#241A12] shadow-sm border border-[#C5A059]/30'
                  : 'text-[#6E5945] hover:text-[#241A12]'
              }`}
            >
              <Users className="w-3.5 h-3.5 text-[#9E742A]" />
              <span>Join Org</span>
            </button>
          </div>

          {/* Error & Success Banners */}
          {error && (
            <div className="mb-5 p-3 rounded-xl bg-red-100 border border-red-300 flex items-start space-x-3 text-red-800 text-xs font-medium">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-5 p-3 rounded-xl bg-emerald-50 border border-emerald-300 flex items-start space-x-3 text-emerald-800 text-xs font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* TAB 1: SIGN IN */}
          {primaryTab === 'signin' && (
            <div>
              {/* Method Selector Tabs */}
              <div className="flex rounded-lg bg-[#F0E8D9] p-1 mb-5 border border-[#C5A059]/20">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMethod('otp');
                    setError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                    authMethod === 'otp'
                      ? 'bg-white text-[#241A12] shadow-xs font-bold'
                      : 'text-[#6E5945] hover:text-[#241A12]'
                  }`}
                >
                  Email OTP
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMethod('password');
                    setError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                    authMethod === 'password'
                      ? 'bg-white text-[#241A12] shadow-xs font-bold'
                      : 'text-[#6E5945] hover:text-[#241A12]'
                  }`}
                >
                  Password
                </button>
              </div>

              {authMethod === 'otp' && (
                <div>
                  {!otpSent ? (
                    <form onSubmit={handleSendOTP} className="space-y-4">
                      <div>
                        <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                          Work / Official Email
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9E742A]">
                            <Mail className="w-4 h-4" />
                          </div>
                          <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@company.com"
                            className={inputStyle}
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={isLoading}
                        className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
                      >
                        <span>{isLoading ? 'Sending Code...' : 'Send Verification OTP'}</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </form>
                  ) : (
                    <form onSubmit={handleVerifyOTP} className="space-y-4">
                      <div>
                        <div className="flex justify-between items-center mb-1.5">
                          <label className="text-xs font-bold text-[#2E2218]">
                            Enter 6-Digit OTP Code
                          </label>
                          <button
                            type="button"
                            onClick={() => {
                              setOtpSent(false);
                              setOtpCode('');
                              setSuccessMsg(null);
                            }}
                            className="text-[11px] text-[#9E742A] hover:underline font-bold"
                          >
                            Change Email
                          </button>
                        </div>
                        <input
                          type="text"
                          maxLength={6}
                          required
                          autoFocus
                          value={otpCode}
                          onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                          placeholder="000000"
                          className="w-full text-center tracking-[0.4em] font-mono text-xl py-3 bg-white border-2 border-[#C5A059]/50 rounded-xl text-[#241A12] font-black focus:outline-none focus:ring-2 focus:ring-[#C5A059]/40 focus:border-[#9E742A] shadow-sm"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={isLoading || otpCode.length < 6}
                        className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
                      >
                        <span>{isLoading ? 'Verifying...' : 'Verify Code & Sign In'}</span>
                        <ShieldCheck className="w-4 h-4" />
                      </button>

                      <div className="text-center pt-2">
                        <button
                          type="button"
                          onClick={handleSendOTP}
                          disabled={isLoading}
                          className="text-xs text-[#5C4A38] hover:text-[#9E742A] font-medium transition-colors"
                        >
                          Didn't receive code? Resend OTP
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}

              {authMethod === 'password' && (
                <form onSubmit={handlePasswordLogin} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                      Email Address
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9E742A]">
                        <Mail className="w-4 h-4" />
                      </div>
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="name@company.com"
                        className={inputStyle}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                      Password
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#9E742A]">
                        <Lock className="w-4 h-4" />
                      </div>
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className={inputStyle}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
                  >
                    <span>{isLoading ? 'Signing In...' : 'Sign In'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              )}

              {/* Google Sign-In */}
              <div className="mt-5">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-[#C5A059]/30" />
                  </div>
                  <div className="relative flex justify-center text-xs">
                    <span className="px-3 bg-[#F9F5EF] text-[#6E5945] font-bold">
                      Or continue with
                    </span>
                  </div>
                </div>

                <div className="mt-3">
                  <button
                    type="button"
                    onClick={handleGoogleAuth}
                    className="w-full flex justify-center items-center px-4 py-2 border border-[#C5A059]/40 rounded-xl text-xs font-bold text-[#2E2218] bg-white hover:bg-[#F8F4EC] hover:border-[#C5A059]/70 shadow-sm transition-all space-x-2.5"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                      />
                    </svg>
                    <span>Continue with Google</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: REGISTER / CREATE ACCOUNT */}
          {primaryTab === 'register' && (
            <div className="space-y-4">
              <div className="text-center mb-2">
                <h3 className="text-sm font-bold text-[#241A12]">Choose Your Account Type</h3>
                <p className="text-xs text-[#6E5945]">Select how you want to use VĀSTU Spatial</p>
              </div>

              {/* Option 1: Register Organization Studio */}
              <Link
                to="/signup/organization"
                className="block p-4 rounded-xl bg-white border-2 border-[#C5A059]/50 hover:border-[#9E742A] shadow-sm hover:shadow-md transition-all group"
              >
                <div className="flex items-start space-x-3.5">
                  <div className="w-10 h-10 rounded-xl bg-[#EDE6DB] border border-[#C5A059]/40 flex items-center justify-center text-[#9E742A] shrink-0 group-hover:scale-105 transition-transform">
                    <Building2 className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-[#241A12]">Register Organization Studio</h4>
                      <ArrowRight className="w-3.5 h-3.5 text-[#9E742A] group-hover:translate-x-1 transition-transform" />
                    </div>
                    <p className="text-[11px] text-[#6E5945] mt-1 leading-snug">
                      For architecture firms, design studios & enterprise teams. Includes GSTIN, multi-member RBAC, and dedicated 3D processing.
                    </p>
                    <span className="inline-block mt-2 text-[10px] font-bold text-[#9E742A] bg-[#EDE6DB]/80 px-2 py-0.5 rounded-md">
                      Enterprise Founder Flow
                    </span>
                  </div>
                </div>
              </Link>

              {/* Option 2: Join Existing Organization */}
              <button
                type="button"
                onClick={() => setPrimaryTab('join')}
                className="w-full text-left p-4 rounded-xl bg-white border border-[#C5A059]/30 hover:border-[#9E742A] shadow-xs hover:shadow-sm transition-all group"
              >
                <div className="flex items-start space-x-3.5">
                  <div className="w-10 h-10 rounded-xl bg-[#EDE6DB] border border-[#C5A059]/40 flex items-center justify-center text-[#9E742A] shrink-0 group-hover:scale-105 transition-transform">
                    <Users className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-[#241A12]">Join an Existing Studio</h4>
                      <ArrowRight className="w-3.5 h-3.5 text-[#9E742A] group-hover:translate-x-1 transition-transform" />
                    </div>
                    <p className="text-[11px] text-[#6E5945] mt-1 leading-snug">
                      Enter the 12-character Organization Code or follow the invite link provided by your studio lead.
                    </p>
                  </div>
                </div>
              </button>

              {/* Option 3: Direct Quick OTP Sign Up */}
              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => {
                    setPrimaryTab('signin');
                    setAuthMethod('otp');
                  }}
                  className="text-xs font-bold text-[#9E742A] hover:underline"
                >
                  Or sign in instantly with OTP
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: JOIN WITH 12-CHAR ORG CODE */}
          {primaryTab === 'join' && (
            <div className="space-y-4">
              <div className="text-center mb-1">
                <h3 className="text-sm font-bold text-[#241A12]">Enter Organization Code</h3>
                <p className="text-xs text-[#6E5945]">Join your team or architecture studio space</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                  12-Character Studio Code
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#9E742A]">
                    <Building className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    maxLength={12}
                    value={joinOrgCode}
                    onChange={(e) => setJoinOrgCode(e.target.value.toUpperCase())}
                    placeholder="e.g. MRXZFQBQD3S"
                    className="w-full pl-10 pr-4 py-3 bg-white border-2 border-[#C5A059]/50 rounded-xl text-[#241A12] font-mono font-bold tracking-widest text-base focus:outline-none focus:ring-2 focus:ring-[#C5A059]/40 focus:border-[#9E742A] shadow-sm uppercase placeholder:text-[#B5A898]"
                  />
                </div>
                <p className="text-[11px] text-[#6E5945] mt-1.5">
                  Founders can view their code on the studio settings or onboarding completion card.
                </p>
              </div>

              <button
                type="button"
                disabled={joinOrgCode.trim().length < 6}
                onClick={() => {
                  const clean = joinOrgCode.trim().toUpperCase();
                  if (clean) {
                    navigate(`/join/${clean}`);
                  }
                }}
                className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <span>Continue to Join Studio</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => setPrimaryTab('signin')}
                  className="text-xs text-[#6E5945] hover:text-[#241A12] font-semibold"
                >
                  Already have an active account? Sign In
                </button>
              </div>
            </div>
          )}

          {/* Bottom Footer Callout */}
          <div className="mt-8 pt-5 border-t border-[#C5A059]/25 text-center flex items-center justify-center space-x-2 text-xs text-[#6E5945]">
            <Compass className="w-3.5 h-3.5 text-[#9E742A]" />
            <span>VĀSTU Spatial Enterprise Cloud v1.0</span>
          </div>
        </div>
      </div>
    </div>
  );
};
