import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { BrandLogo } from '../../components/brand/BrandLogo';
import { AccountSetupLoader } from '../../components/brand/AccountSetupLoader';
import {
  Building2,
  User,
  Shield,
  MapPin,
  FileCheck,
  CheckCircle,
  Copy,
  Check,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  Share2,
  MessageCircle,
  UploadCloud
} from 'lucide-react';

export const OrganizationSignupPage: React.FC = () => {
  const navigate = useNavigate();
  const { setSession } = useAuth();

  // Restore draft state if present in sessionStorage
  const savedDraft = (() => {
    try {
      const d = sessionStorage.getItem('vastu_org_signup_draft');
      return d ? JSON.parse(d) : {};
    } catch {
      return {};
    }
  })();

  const [step, setStep] = useState<number>(savedDraft.step || 1);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmittingRegistration, setIsSubmittingRegistration] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 1: Founder details & OTP
  const [applicantName, setApplicantName] = useState(savedDraft.applicantName || '');
  const [email, setEmail] = useState(savedDraft.email || '');
  const [phone, setPhone] = useState(savedDraft.phone || '');
  const [password, setPassword] = useState(savedDraft.password || '');
  const [otpSent, setOtpSent] = useState(savedDraft.otpSent || false);
  const [otpCode, setOtpCode] = useState('');
  const [isEmailVerified, setIsEmailVerified] = useState(savedDraft.isEmailVerified || false);

  // Step 2: Org details
  const [organizationName, setOrganizationName] = useState(savedDraft.organizationName || '');
  const [legalName, setLegalName] = useState(savedDraft.legalName || '');
  const [organizationType, setOrganizationType] = useState(savedDraft.organizationType || 'Enterprise');
  const [industry, setIndustry] = useState(savedDraft.industry || 'Construction & Engineering');
  const [website, setWebsite] = useState(savedDraft.website || '');
  const [officialEmail, setOfficialEmail] = useState(savedDraft.officialEmail || '');
  const [officialPhone, setOfficialPhone] = useState(savedDraft.officialPhone || '');
  const [numberOfEmployees, setNumberOfEmployees] = useState(savedDraft.numberOfEmployees || '11-50');
  const [yearEstablished, setYearEstablished] = useState<number>(savedDraft.yearEstablished || 2024);
  const [description, setDescription] = useState(savedDraft.description || '');

  // Step 3: Identifiers & Document
  const [identifierType, setIdentifierType] = useState(savedDraft.identifierType || 'GSTIN');
  const [identifierValue, setIdentifierValue] = useState(savedDraft.identifierValue || '');
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentName, setDocumentName] = useState(savedDraft.documentName || '');

  // Step 4: Address
  const [addressLine1, setAddressLine1] = useState(savedDraft.addressLine1 || '');
  const [addressLine2, setAddressLine2] = useState(savedDraft.addressLine2 || '');
  const [locality, setLocality] = useState(savedDraft.locality || '');
  const [city, setCity] = useState(savedDraft.city || '');
  const [state, setState] = useState(savedDraft.state || '');
  const [pincode, setPincode] = useState(savedDraft.pincode || '');
  const [country, setCountry] = useState(savedDraft.country || 'India');

  // Save draft state across steps
  useEffect(() => {
    if (step < 6) {
      sessionStorage.setItem(
        'vastu_org_signup_draft',
        JSON.stringify({
          step,
          applicantName,
          email,
          phone,
          password,
          otpSent,
          isEmailVerified,
          organizationName,
          legalName,
          organizationType,
          industry,
          website,
          officialEmail,
          officialPhone,
          numberOfEmployees,
          yearEstablished,
          description,
          identifierType,
          identifierValue,
          documentName,
          addressLine1,
          addressLine2,
          locality,
          city,
          state,
          pincode,
          country,
        })
      );
    }
  }, [
    step,
    applicantName,
    email,
    phone,
    password,
    otpSent,
    isEmailVerified,
    organizationName,
    legalName,
    organizationType,
    industry,
    website,
    officialEmail,
    officialPhone,
    numberOfEmployees,
    yearEstablished,
    description,
    identifierType,
    identifierValue,
    documentName,
    addressLine1,
    addressLine2,
    locality,
    city,
    state,
    pincode,
    country,
  ]);

  // Step 5 Result:
  const [createdOrg, setCreatedOrg] = useState<{
    org_code: string;
    name: string;
    invite_url: string;
    whatsapp_message: string;
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  // Password validation helper
  const validatePasswordStrength = (pwd: string) => {
    if (pwd.length < 12) return 'Password must be at least 12 characters';
    if (!/[A-Z]/.test(pwd)) return 'Password must contain at least one uppercase letter';
    if (!/[a-z]/.test(pwd)) return 'Password must contain at least one lowercase letter';
    if (!/[0-9]/.test(pwd)) return 'Password must contain at least one number';
    if (!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pwd)) return 'Password must contain at least one special character';
    return null;
  };

  const handleSendFounderOTP = async () => {
    if (!email) {
      setError('Please provide an email address');
      return;
    }
    const pwdErr = validatePasswordStrength(password);
    if (pwdErr) {
      setError(pwdErr);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await api.sendOTP(email, 'ORG_SIGNUP');
      setOtpSent(true);
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch verification OTP');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyFounderOTP = async () => {
    if (!otpCode || otpCode.length < 6) {
      setError('Enter 6-digit OTP');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await api.verifyOTP(email, otpCode, 'ORG_SIGNUP');
      setIsEmailVerified(true);
    } catch (err: any) {
      setError(err.message || 'Invalid verification OTP');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStep1Next = () => {
    if (!applicantName || !email || !phone || !password) {
      setError('All founder fields are required');
      return;
    }
    if (!isEmailVerified) {
      setError('Please verify your work email address with the OTP before proceeding');
      return;
    }
    setError(null);
    setStep(2);
  };

  const handleStep2Next = () => {
    if (!organizationName) {
      setError('Organization name is required');
      return;
    }
    setError(null);
    setStep(3);
  };

  const handleStep3Next = () => {
    if (identifierType === 'GSTIN' && identifierValue) {
      const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
      if (!gstinRegex.test(identifierValue.trim().toUpperCase())) {
        setError('Invalid GSTIN format. Expected 15 characters (e.g. 29AAAAA0000A1Z5)');
        return;
      }
    }
    setError(null);
    setStep(4);
  };

  const handleStep4Next = () => {
    if (!addressLine1 || !city || !state || !pincode) {
      setError('Please provide Address Line 1, City, State, and Pincode');
      return;
    }
    if (pincode.replace(/\D/g, '').length !== 6) {
      setError('Postal PIN code must be 6 digits');
      return;
    }
    setError(null);
    setStep(5);
  };

  const handleAtomicSubmit = async () => {
    setIsSubmittingRegistration(true);
    setIsLoading(true);
    setError(null);
    try {
      const payload = {
        applicant_name: applicantName,
        email: email.trim().toLowerCase(),
        phone: phone.trim(),
        password: password,
        organization_name: organizationName.trim(),
        legal_name: legalName ? legalName.trim() : organizationName.trim(),
        organization_type: organizationType,
        industry: industry,
        official_email: officialEmail ? officialEmail.trim().toLowerCase() : email.trim().toLowerCase(),
        official_phone: officialPhone ? officialPhone.trim() : phone.trim(),
        website: website.trim(),
        number_of_employees: numberOfEmployees,
        year_established: Number(yearEstablished) || 2024,
        description: description.trim(),
        identifier_type: identifierType,
        identifier_value: identifierValue.trim().toUpperCase(),
        document_name: documentName || (documentFile ? documentFile.name : undefined),
        document_url: documentFile ? `/uploads/${documentFile.name}` : undefined,
        document_type: identifierType === 'GSTIN' ? 'GST Certificate' : 'Business Registration Document',
        address_line1: addressLine1.trim(),
        address_line2: addressLine2.trim(),
        locality: locality.trim(),
        city: city.trim(),
        state: state.trim(),
        country: country.trim() || 'India',
        pincode: pincode.trim(),
      };

      const res = await api.completeOrganizationSignup(payload);

      // Save tokens in session
      setSession({
        user: res.user,
        tokens: res.tokens,
        activeOrg: {
          id: res.organization.id,
          org_code: res.organization.org_code,
          name: res.organization.name,
          legal_name: res.organization.legal_name,
          status: 'active',
          created_at: new Date().toISOString(),
        },
      });

      setCreatedOrg({
        org_code: res.organization.org_code,
        name: res.organization.name,
        invite_url: res.invite.invite_url,
        whatsapp_message: res.invite.whatsapp_message,
      });

      sessionStorage.removeItem('vastu_org_signup_draft');
      setStep(6);
    } catch (err: any) {
      setError(err.message || 'Failed to complete organization registration');
    } finally {
      setIsLoading(false);
      setIsSubmittingRegistration(false);
    }
  };

  const copyOrgCode = () => {
    if (createdOrg?.org_code) {
      navigator.clipboard.writeText(createdOrg.org_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  const copyInviteLink = () => {
    if (createdOrg?.invite_url) {
      navigator.clipboard.writeText(createdOrg.invite_url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const fieldStyle =
    'input-brand w-full px-3.5 py-2.5 bg-white border border-[#C5A059]/40 hover:border-[#C5A059]/70 rounded-xl text-[#241A12] text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#C5A059]/30 focus:border-[#9E742A] placeholder-[#9C8E7E] shadow-sm transition-all';

  if (isSubmittingRegistration) {
    return (
      <AccountSetupLoader
        message="Please wait till we setup your account"
        submessage="Configuring your organization workspace, spatial registry & encryption keys..."
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden flex flex-col justify-center">
      {/* Brand Warm Glow background */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[750px] h-[380px] bg-[#C5A059]/15 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[400px] h-[400px] bg-[#B08940]/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-3xl mx-auto w-full relative z-10">
        {/* Header */}
        <div className="text-center mb-8">
          <Link
            to="/login"
            className="inline-flex items-center space-x-2 text-xs font-semibold text-[#695541] hover:text-[#2B2219] mb-4 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Login</span>
          </Link>
          <div className="flex justify-center items-center mb-3">
            <BrandLogo size="lg" showTagline theme="light" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#2B2219] font-serif-brand">
            Organization Onboarding
          </h1>
          <p className="text-xs text-[#695541] mt-1">
            Establish your digital twin and spatial engineering workspace in 5 steps
          </p>
        </div>

        {/* Step Progress Indicator */}
        {step <= 5 && (
          <div className="flex items-center justify-between mb-8 px-4 sm:px-8">
            {[
              { num: 1, label: 'Founder' },
              { num: 2, label: 'Profile' },
              { num: 3, label: 'Identifiers' },
              { num: 4, label: 'Address' },
              { num: 5, label: 'Review' },
            ].map((s) => (
              <div key={s.num} className="flex flex-col items-center">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    step === s.num
                      ? 'bg-[#8F6834] text-white font-black shadow-lg shadow-[#8F6834]/30 ring-4 ring-[#C5A059]/30'
                      : step > s.num
                      ? 'bg-[#EDE6DB] border-2 border-[#8F6834] text-[#8F6834]'
                      : 'bg-[#EDE6DB] border border-[#C5A059]/30 text-[#8C7A68]'
                  }`}
                >
                  {step > s.num ? '✓' : s.num}
                </div>
                <span
                  className={`text-[10px] mt-1.5 font-medium ${
                    step === s.num
                      ? 'text-[#8F6834] font-bold'
                      : step > s.num
                      ? 'text-[#695541] font-semibold'
                      : 'text-[#8C7A68]'
                  }`}
                >
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Form Container */}
        <div className="glass-panel rounded-2xl p-6 sm:p-8 shadow-2xl border border-[#C5A059]/30">
          {error && (
            <div className="mb-6 p-3.5 rounded-xl bg-red-950/60 border border-red-800/80 flex items-start space-x-3 text-red-200 text-xs">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* STEP 1: Founder Identity */}
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-base font-bold text-[#2B2219] flex items-center space-x-2 font-serif-brand">
                  <User className="w-4 h-4 text-[#8F6834]" />
                  <span>Founder & Workspace Administrator</span>
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  You will be designated as the permanent Organization Owner.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Full Legal Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={applicantName}
                    onChange={(e) => setApplicantName(e.target.value)}
                    placeholder="e.g. Ramesh Kumar"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Mobile Phone *
                  </label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className={fieldStyle}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                  Founder Password * (Min. 12 characters, uppercase, lowercase, number, symbol)
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className={fieldStyle}
                />
              </div>

              {/* Email + OTP Verification block */}
              <div className="p-4 rounded-xl bg-white border border-[#C5A059]/35 space-y-3 shadow-sm">
                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Work Email *
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="email"
                      required
                      disabled={isEmailVerified}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="founder@company.com"
                      className={`${fieldStyle} flex-1 disabled:opacity-60`}
                    />
                    {!isEmailVerified && (
                      <button
                        type="button"
                        onClick={handleSendFounderOTP}
                        disabled={isLoading || !email}
                        className="px-4 py-2.5 bg-[#FAF7F2] hover:bg-[#F2ECE0] border border-[#C5A059]/50 text-[#8F6834] text-xs font-bold rounded-xl transition-all whitespace-nowrap shadow-sm"
                      >
                        {otpSent ? 'Resend OTP' : 'Send OTP'}
                      </button>
                    )}
                  </div>
                </div>

                {otpSent && !isEmailVerified && (
                  <div className="flex items-center space-x-2 pt-2">
                    <input
                      type="text"
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                      placeholder="6-digit OTP"
                      className="w-36 text-center font-mono py-2 bg-white border-2 border-[#C5A059]/50 rounded-xl text-[#241A12] font-black text-sm focus:outline-none focus:ring-2 focus:ring-[#C5A059]/30 focus:border-[#9E742A] shadow-sm"
                    />
                    <button
                      type="button"
                      onClick={handleVerifyFounderOTP}
                      disabled={isLoading || otpCode.length < 6}
                      className="btn-brand-primary px-4 py-2 text-xs font-bold rounded-xl shadow"
                    >
                      Verify Email
                    </button>
                  </div>
                )}

                {isEmailVerified && (
                  <div className="flex items-center space-x-2 text-emerald-700 text-xs font-bold pt-1">
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                    <span>Email verified successfully</span>
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-4">
                <button
                  type="button"
                  onClick={handleStep1Next}
                  className="btn-brand-primary py-2.5 px-6 rounded-xl text-sm font-bold flex items-center space-x-2"
                >
                  <span>Continue to Organization Profile</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Organization Profile */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-base font-bold text-[#2B2219] flex items-center space-x-2 font-serif-brand">
                  <Building2 className="w-4 h-4 text-[#8F6834]" />
                  <span>Organization Profile</span>
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  General details for your company's space on VĀSTU.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Organization / Brand Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder="e.g. Apex Engineering Labs"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Legal Business Name
                  </label>
                  <input
                    type="text"
                    value={legalName}
                    onChange={(e) => setLegalName(e.target.value)}
                    placeholder="Apex Engineering Labs Private Limited"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Organization Type
                  </label>
                  <select
                    value={organizationType}
                    onChange={(e) => setOrganizationType(e.target.value)}
                    className={fieldStyle}
                  >
                    <option value="Enterprise">Enterprise</option>
                    <option value="General Contractor">General Contractor</option>
                    <option value="Architectural Firm">Architectural Firm</option>
                    <option value="Surveying & Photogrammetry">Surveying & Photogrammetry</option>
                    <option value="Govt Agency">Govt Agency</option>
                    <option value="Consultancy">Consultancy</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Industry Domain
                  </label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className={fieldStyle}
                  >
                    <option value="Construction & Engineering">Construction & Engineering</option>
                    <option value="Real Estate & Infrastructure">Real Estate & Infrastructure</option>
                    <option value="Mining & Quarrying">Mining & Quarrying</option>
                    <option value="Archaeology & Heritage">Archaeology & Heritage</option>
                    <option value="Smart Cities & Digital Twins">Smart Cities & Digital Twins</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Official Website
                  </label>
                  <input
                    type="url"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    placeholder="https://apexengineering.io"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Team Size
                  </label>
                  <select
                    value={numberOfEmployees}
                    onChange={(e) => setNumberOfEmployees(e.target.value)}
                    className={fieldStyle}
                  >
                    <option value="1-10">1-10 Employees</option>
                    <option value="11-50">11-50 Employees</option>
                    <option value="51-200">51-200 Employees</option>
                    <option value="201-1000">201-1000 Employees</option>
                    <option value="1000+">1000+ Employees</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                  Brief Overview / Description
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Specialists in LiDAR point cloud acquisition and BIM synchronization..."
                  className={fieldStyle}
                />
              </div>

              <div className="flex justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="btn-brand-secondary py-2.5 px-5 rounded-xl text-sm font-bold shadow-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleStep2Next}
                  className="btn-brand-primary py-2.5 px-6 rounded-xl text-sm font-bold flex items-center space-x-2"
                >
                  <span>Continue to Identifiers</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Identifiers & Document Upload */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-base font-bold text-[#2B2219] flex items-center space-x-2 font-serif-brand">
                  <Shield className="w-4 h-4 text-[#8F6834]" />
                  <span>Business Identifiers & Verification</span>
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  Provide your organization tax or registration number.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Identifier Type
                  </label>
                  <select
                    value={identifierType}
                    onChange={(e) => setIdentifierType(e.target.value)}
                    className={fieldStyle}
                  >
                    <option value="GSTIN">GSTIN (India 15-char)</option>
                    <option value="PAN">PAN (10-char)</option>
                    <option value="UDYAM">UDYAM Registration</option>
                    <option value="SHOP_ACT">Shop & Establishment Act</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    {identifierType} Value
                  </label>
                  <input
                    type="text"
                    value={identifierValue}
                    onChange={(e) => setIdentifierValue(e.target.value.toUpperCase())}
                    placeholder={identifierType === 'GSTIN' ? '29AAAAA0000A1Z5' : 'AAAAA0000A'}
                    className={`${fieldStyle} font-mono uppercase`}
                  />
                </div>
              </div>

              {/* Supporting Document */}
              <div className="p-4 rounded-xl bg-white border border-[#C5A059]/35 shadow-sm space-y-3">
                <label className="block text-xs font-bold text-[#2E2218]">
                  Supporting Verification Document (Optional PDF / Certificate)
                </label>
                <div className="border-2 border-dashed border-[#C5A059]/40 bg-[#FAF7F2] rounded-xl p-4 text-center hover:border-[#C5A059] transition-colors">
                  <UploadCloud className="w-8 h-8 text-[#8F6834] mx-auto mb-2" />
                  <input
                    type="file"
                    id="doc-upload"
                    accept=".pdf,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setDocumentFile(e.target.files[0]);
                        setDocumentName(e.target.files[0].name);
                      }
                    }}
                  />
                  <label
                    htmlFor="doc-upload"
                    className="cursor-pointer text-xs font-bold text-[#2E2218] hover:text-[#8F6834] transition-colors"
                  >
                    {documentName ? documentName : 'Click to select Certificate or Registration PDF'}
                  </label>
                  <p className="text-[10px] text-[#736A5E] mt-1">PDF, PNG, or JPG up to 15MB</p>
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="btn-brand-secondary py-2.5 px-5 rounded-xl text-sm font-bold shadow-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleStep3Next}
                  className="btn-brand-primary py-2.5 px-6 rounded-xl text-sm font-bold flex items-center space-x-2"
                >
                  <span>Continue to Address</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Primary Address */}
          {step === 4 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-base font-bold text-[#2B2219] flex items-center space-x-2 font-serif-brand">
                  <MapPin className="w-4 h-4 text-[#8F6834]" />
                  <span>Registered Business Address</span>
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  Primary corporate location for regulatory and billing verification.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                  Address Line 1 *
                </label>
                <input
                  type="text"
                  required
                  value={addressLine1}
                  onChange={(e) => setAddressLine1(e.target.value)}
                  placeholder="Street / Building No / Tech Park"
                  className={fieldStyle}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Address Line 2
                  </label>
                  <input
                    type="text"
                    value={addressLine2}
                    onChange={(e) => setAddressLine2(e.target.value)}
                    placeholder="Floor / Wing / Suite"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Locality / Area
                  </label>
                  <input
                    type="text"
                    value={locality}
                    onChange={(e) => setLocality(e.target.value)}
                    placeholder="e.g. Whitefield"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    City *
                  </label>
                  <input
                    type="text"
                    required
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Bengaluru"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    State *
                  </label>
                  <input
                    type="text"
                    required
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    placeholder="Karnataka"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    PIN Code * (6 digits)
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    value={pincode}
                    onChange={(e) => setPincode(e.target.value.replace(/\D/g, ''))}
                    placeholder="560066"
                    className={fieldStyle}
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2E2218] mb-1.5">
                    Country
                  </label>
                  <input
                    type="text"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className={fieldStyle}
                  />
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="btn-brand-secondary py-2.5 px-5 rounded-xl text-sm font-bold shadow-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleStep4Next}
                  className="btn-brand-primary py-2.5 px-6 rounded-xl text-sm font-bold flex items-center space-x-2"
                >
                  <span>Review Summary</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: Review & Submit (Atomic Transaction Trigger) */}
          {step === 5 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-base font-bold text-[#2B2219] flex items-center space-x-2 font-serif-brand">
                  <FileCheck className="w-4 h-4 text-[#8F6834]" />
                  <span>Review & Complete Registration</span>
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  Confirm the details below. Once submitted, your organization space and unambiguous 12-character ID will be generated atomically.
                </p>
              </div>

              <div className="bg-white rounded-xl p-5 border border-[#C5A059]/35 shadow-sm space-y-4 text-xs">
                <div className="border-b border-[#E8DEC9] pb-3">
                  <span className="text-[#8F6834] uppercase text-[10px] tracking-wider font-bold">Founder Account</span>
                  <div className="text-[#1F150D] font-bold text-sm mt-1">{applicantName}</div>
                  <div className="text-[#5A4838]">{email} • {phone}</div>
                  <div className="text-[#8F6834] text-[11px] mt-1 flex items-center space-x-1 font-semibold">
                    <Check className="w-3.5 h-3.5 text-[#8F6834]" />
                    <span>Email OTP Verified</span>
                  </div>
                </div>

                <div className="border-b border-[#E8DEC9] pb-3">
                  <span className="text-[#8F6834] uppercase text-[10px] tracking-wider font-bold">Organization Profile</span>
                  <div className="text-[#1F150D] font-bold text-sm mt-1">{organizationName}</div>
                  <div className="text-[#5A4838]">{legalName || organizationName}</div>
                  <div className="text-[#736A5E] mt-0.5">{organizationType} • {industry}</div>
                </div>

                {identifierValue && (
                  <div className="border-b border-[#E8DEC9] pb-3">
                    <span className="text-[#8F6834] uppercase text-[10px] tracking-wider font-bold">Identifier</span>
                    <div className="text-[#1F150D] font-mono font-bold mt-1">{identifierType}: {identifierValue}</div>
                  </div>
                )}

                <div>
                  <span className="text-[#8F6834] uppercase text-[10px] tracking-wider font-bold">Address</span>
                  <div className="text-[#5A4838] mt-1">
                    {addressLine1}, {locality ? locality + ', ' : ''}{city}, {state} - {pincode}, {country}
                  </div>
                </div>
              </div>

              <div className="flex justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setStep(4)}
                  className="btn-brand-secondary py-2.5 px-5 rounded-xl text-sm font-bold shadow-sm"
                >
                  Back
                </button>
                <button
                  type="button"
                  disabled={isLoading}
                  onClick={handleAtomicSubmit}
                  className="btn-brand-primary py-3 px-8 rounded-xl text-sm font-bold flex items-center space-x-2 disabled:opacity-50"
                >
                  <span>{isLoading ? 'Creating Workspace...' : 'Confirm & Launch Workspace'}</span>
                  <CheckCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 6: Success / 12-char Org Code & WhatsApp Share Screen */}
          {step === 6 && createdOrg && (
            <div className="text-center py-6 space-y-6">
              <div className="w-16 h-16 bg-[#EDE6DB] border border-[#8F6834] rounded-full flex items-center justify-center mx-auto shadow-xl shadow-[#8F6834]/20 text-[#8F6834]">
                <CheckCircle className="w-10 h-10" />
              </div>

              <div>
                <h2 className="text-xl font-bold text-[#2B2219] font-serif-brand">
                  {createdOrg.name} Space Created!
                </h2>
                <p className="text-xs text-[#695541] mt-1">
                  You are registered as the Organization Founder and Owner.
                </p>
              </div>

              {/* 12-char Org Code Card */}
              <div className="p-6 rounded-2xl bg-[#241A13] border border-[#C5A059]/50 text-center space-y-2 max-w-md mx-auto shadow-2xl">
                <span className="text-[10px] uppercase font-bold text-[#F2DFB8] tracking-wider">
                  Official 12-Character Organization Code
                </span>
                <div className="flex items-center justify-center space-x-3">
                  <span className="font-mono text-2xl font-black text-white tracking-[0.2em]">
                    {createdOrg.org_code}
                  </span>
                  <button
                    onClick={copyOrgCode}
                    className="p-2.5 rounded-xl bg-[#3D2C1F] hover:bg-[#4E3827] border border-[#C5A059]/50 text-[#F2DFB8] transition-colors"
                    title="Copy Org Code"
                  >
                    {copiedCode ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[11px] text-[#C4B9AC]">
                  Share this code or invitation link with your team members to join.
                </p>
              </div>

              {/* Invite Actions: WhatsApp & Copy */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(createdOrg.whatsapp_message)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-[#25D366] hover:bg-[#20bd5a] text-black font-bold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-[#25D366]/20 transition-all"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>Share Invite via WhatsApp</span>
                </a>

                <button
                  type="button"
                  onClick={copyInviteLink}
                  className="btn-brand-secondary w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 shadow-sm"
                >
                  {copiedLink ? <Check className="w-4 h-4 text-[#8F6834]" /> : <Share2 className="w-4 h-4 text-[#8F6834]" />}
                  <span>{copiedLink ? 'Link Copied' : 'Copy Join Link'}</span>
                </button>
              </div>

              <div className="pt-6">
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="btn-brand-primary py-3 px-8 rounded-xl text-sm font-bold flex items-center justify-center space-x-2 mx-auto"
                >
                  <span>Enter Control Plane Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
