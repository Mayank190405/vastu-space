import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { BrandLogo } from '../../components/brand/BrandLogo';
import { AccountSetupLoader } from '../../components/brand/AccountSetupLoader';
import { Building2, User, Mail, Phone, Lock, ArrowRight, ShieldCheck, AlertCircle, CheckCircle2, Clock } from 'lucide-react';

export const EmployeeJoinPage: React.FC = () => {
  const { orgCode: urlOrgCode, inviteToken } = useParams<{ orgCode?: string; inviteToken?: string }>();
  const navigate = useNavigate();
  const { setSession } = useAuth();

  const [inputOrgCode, setInputOrgCode] = useState(urlOrgCode || '');
  const [isValidating, setIsValidating] = useState(Boolean(urlOrgCode && inviteToken));
  const [orgData, setOrgData] = useState<{ organization_name: string; org_code: string } | null>(
    urlOrgCode ? { organization_name: 'Studio Workspace', org_code: urlOrgCode.toUpperCase() } : null
  );
  const [validationError, setValidationError] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [isEmailVerified, setIsEmailVerified] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const validate = async () => {
      if (urlOrgCode && inviteToken) {
        try {
          setIsValidating(true);
          const res = await api.validateInvite(urlOrgCode, inviteToken);
          setOrgData(res);
        } catch (err: any) {
          setValidationError(err.message || 'This invitation link is invalid or has expired.');
        } finally {
          setIsValidating(false);
        }
      } else if (urlOrgCode) {
        setOrgData({ organization_name: 'Studio Workspace', org_code: urlOrgCode.toUpperCase() });
        setIsValidating(false);
      } else {
        setIsValidating(false);
      }
    };
    validate();
  }, [urlOrgCode, inviteToken]);

  const handleSendOTP = async () => {
    if (!email) {
      setSubmitError('Please enter your official email');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await api.sendOTP(email, 'EMPLOYEE_SIGNUP');
      setOtpSent(true);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to dispatch verification OTP');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (!otpCode || otpCode.length < 6) {
      setSubmitError('Please enter the 6-digit OTP');
      return;
    }
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await api.verifyOTP(email, otpCode, 'EMPLOYEE_SIGNUP');
      setIsEmailVerified(true);
    } catch (err: any) {
      setSubmitError(err.message || 'Invalid verification OTP');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    const effectiveOrgCode = (inputOrgCode || urlOrgCode || '').trim().toUpperCase();
    if (!effectiveOrgCode) {
      setSubmitError('Please enter a valid 12-character Organization Code');
      return;
    }
    if (!fullName || !email || !password) {
      setSubmitError('Please fill in all required fields');
      return;
    }
    if (!isEmailVerified) {
      setSubmitError('Please verify your email address using the OTP code');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const res = await api.submitEmployeeJoin({
        org_code: effectiveOrgCode,
        invite_token: inviteToken || '',
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim(),
        password: password,
      });

      setSession({
        user: res.user,
        tokens: res.tokens,
        memberships: [
          {
            id: res.join_request?.id || 'req_new',
            org_id: res.organization?.id || '',
            user_id: res.user.id,
            role: 'member',
            status: 'invited',
            created_at: new Date().toISOString(),
          },
        ],
      });

      setOrgData({
        organization_name: res.organization?.name || 'Studio Workspace',
        org_code: effectiveOrgCode,
      });
      setSubmitted(true);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to submit join request');
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputStyle =
    'input-brand w-full px-3.5 py-2.5 bg-white border border-[#C5A059]/40 hover:border-[#8F6834] rounded-xl text-[#241A12] text-sm focus:outline-none focus:ring-2 focus:ring-[#8F6834]/20 focus:border-[#8F6834] placeholder-[#9C8E7E] transition-all shadow-sm';

  if (isSubmitting) {
    return (
      <AccountSetupLoader
        message="Please wait till we setup your account"
        submessage="Registering employee profile and connecting with organization workspace..."
      />
    );
  }

  if (isValidating) {
    return (
      <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-2 border-[#8F6834] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-semibold text-[#8F6834]">Verifying Organization Invitation...</p>
        </div>
      </div>
    );
  }

  if (validationError || !orgData) {
    return (
      <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex items-center justify-center p-4">
        <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-red-900/40 text-center space-y-4">
          <div className="w-12 h-12 bg-red-950/60 border border-red-800 rounded-full flex items-center justify-center mx-auto text-red-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-[#2B2219] font-serif-brand">Invalid or Expired Invitation</h2>
          <p className="text-xs text-[#695541]">{validationError}</p>
          <div className="pt-2">
            <Link
              to="/login"
              className="btn-brand-secondary inline-block py-2.5 px-6 rounded-xl text-xs font-bold transition-all shadow-sm"
            >
              Return to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex items-center justify-center p-4">
        <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-[#C5A059]/30 text-center space-y-5">
          <div className="w-14 h-14 bg-[#EDE6DB] border border-[#8F6834] rounded-full flex items-center justify-center mx-auto text-[#8F6834]">
            <Clock className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-bold text-[#2B2219] font-serif-brand">Join Request Submitted</h2>
          <p className="text-xs text-[#695541] leading-relaxed">
            Your request to join <strong className="text-[#2B2219] font-bold">{orgData.organization_name}</strong> has been sent to the workspace administrator.
          </p>
          <div className="p-3 bg-white rounded-xl border border-[#C5A059]/35 text-xs text-[#8F6834] font-bold shadow-sm">
            Current Status: <span className="font-bold text-[#8F6834]">PENDING APPROVAL</span>
          </div>
          <button
            onClick={() => navigate('/pending-approval')}
            className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all"
          >
            Go to Approval Status Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden flex flex-col justify-center">
      <div className="max-w-md mx-auto w-full relative z-10">
        <div className="text-center mb-6">
          <div className="flex justify-center items-center mb-2">
            <BrandLogo size="md" theme="light" />
          </div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#EDE6DB] border border-[#C5A059]/40 text-[#8F6834] text-xs font-semibold mb-3">
            <Building2 className="w-3.5 h-3.5" />
            <span>{inviteToken ? 'Invitation to Join Workspace' : 'Join Studio Workspace'}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#2B2219] font-serif-brand">
            {orgData?.organization_name || 'Organization Workspace'}
          </h1>
          {urlOrgCode && (
            <p className="text-xs text-[#8F6834] mt-1 font-mono font-semibold">Org Code: {urlOrgCode.toUpperCase()}</p>
          )}
        </div>

        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#C5A059]/25 shadow-2xl">
          {submitError && (
            <div className="mb-5 p-3 rounded-xl bg-red-100 border border-red-300 flex items-start space-x-2 text-red-800 text-xs font-medium">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{submitError}</span>
            </div>
          )}

          <form onSubmit={handleSubmitJoin} className="space-y-4">
            {!urlOrgCode && (
              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                  12-Character Organization Code *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8F6834]">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    maxLength={12}
                    value={inputOrgCode}
                    onChange={(e) => setInputOrgCode(e.target.value.toUpperCase())}
                    placeholder="e.g. MRXZFQBQD3S"
                    className={`${inputStyle} pl-10 font-mono tracking-widest uppercase font-bold`}
                  />
                </div>
                <p className="text-[11px] text-[#695541] mt-1">
                  Ask your studio administrator for their 12-character permanent organization code.
                </p>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-[#2E2218] mb-1.5">Full Name *</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8F6834]">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Priya Sharma"
                  className={`${inputStyle} pl-10`}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#2E2218] mb-1.5">Mobile Phone (Optional)</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8F6834]">
                  <Phone className="w-4 h-4" />
                </div>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98765 43210"
                  className={`${inputStyle} pl-10`}
                />
              </div>
            </div>

            {/* Email + OTP Verification */}
            <div className="p-4 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/35 space-y-3 shadow-inner">
              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">Work Email *</label>
                <div className="flex space-x-2">
                  <input
                    type="email"
                    required
                    disabled={isEmailVerified}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className={`${inputStyle} flex-1 disabled:opacity-60`}
                  />
                  {!isEmailVerified && (
                    <button
                      type="button"
                      onClick={handleSendOTP}
                      disabled={isSubmitting || !email}
                      className="btn-brand-secondary px-4 py-2 text-xs font-bold rounded-xl whitespace-nowrap shadow-sm"
                    >
                      {otpSent ? 'Resend' : 'Send OTP'}
                    </button>
                  )}
                </div>
              </div>

              {otpSent && !isEmailVerified && (
                <div className="flex items-center space-x-2 pt-1">
                  <input
                    type="text"
                    maxLength={6}
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="6-digit OTP"
                    className="w-32 text-center font-mono py-2 bg-white border border-[#C5A059]/50 rounded-xl text-[#1F150D] font-bold text-xs focus:outline-none focus:ring-2 focus:ring-[#8F6834]/20 focus:border-[#8F6834] shadow-sm"
                  />
                  <button
                    type="button"
                    onClick={handleVerifyOTP}
                    disabled={isSubmitting || otpCode.length < 6}
                    className="btn-brand-primary px-4 py-2 text-xs font-bold rounded-xl shadow-sm"
                  >
                    Verify
                  </button>
                </div>
              )}

              {isEmailVerified && (
                <div className="flex items-center space-x-1.5 text-[#8F6834] text-xs font-bold">
                  <CheckCircle2 className="w-4 h-4 text-[#8F6834]" />
                  <span>Email verified</span>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-[#2E2218] mb-1.5">Create Account Password *</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8F6834]">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 12 characters"
                  className={`${inputStyle} pl-10`}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !isEmailVerified}
              className="btn-brand-primary w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <span>{isSubmitting ? 'Submitting Request...' : 'Submit Join Request'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-5 text-center text-xs text-[#695541]">
            Already have an active account?{' '}
            <Link to="/login" className="text-[#8F6834] font-bold hover:underline">
              Log In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
