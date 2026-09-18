import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2,
  MapPin,
  Users,
  Layers,
  FileUp,
  PencilRuler,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Upload,
  Save,
  Trash2,
  Plus,
  Loader2,
  AlertCircle,
  HelpCircle,
  X
} from 'lucide-react';
import { api } from '../../services/api';
import { LocationSearchInput } from '../../components/location/LocationSearchInput';
import { FloorPlanDrawer } from '../../components/canvas/FloorPlanDrawer';
import {
  ProjectTypeDefinition,
  CreateFloorInput,
  AssignProjectMemberInput,
  OrganizationMember,
  ProjectCreationFullInput,
  FloorPlanDrawingData
} from '../../types';

interface FloorPlanDraftState {
  planType: 'UPLOADED' | 'DRAWN';
  file?: File;
  fileName?: string;
  previewUrl?: string;
  drawingData?: FloorPlanDrawingData;
  drawingPreviewBase64?: string;
}

export const ProjectCreationWizard: React.FC = () => {
  const navigate = useNavigate();

  // Wizard Navigation
  const [currentStep, setCurrentStep] = useState<number>(1);
  const totalSteps = 6;

  // Global Project State
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState('Building');
  const [customType, setCustomType] = useState('');
  const [description, setDescription] = useState('');

  // Cover Image
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string>('');
  const [coverImageId, setCoverImageId] = useState<string>('');
  const [coverImageUrl, setCoverImageUrl] = useState<string>('');
  const [isUploadingCover, setIsUploadingCover] = useState(false);

  // Contact Info
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactEmail, setContactEmail] = useState('');

  // Address
  const [address, setAddress] = useState<{
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
  }>({
    address_line_1: '',
    address_line_2: '',
    area: '',
    city: '',
    state: '',
    pincode: '',
    country: 'India',
    latitude: undefined,
    longitude: undefined,
    place_id: undefined,
  });

  // Floors
  const [floors, setFloors] = useState<CreateFloorInput[]>([
    {
      name: 'Ground Floor',
      floor_number: 0,
      floor_type: 'Ground Floor',
      area_value: 2500,
      area_unit: 'SQFT',
      height_value: 10.5,
      height_unit: 'FT',
      sequence: 1,
      description: '',
    },
  ]);

  // Floor Plans mapped by floor index
  const [floorPlans, setFloorPlans] = useState<Record<number, FloorPlanDraftState>>({});
  const [activeDrawingFloorIndex, setActiveDrawingFloorIndex] = useState<number | null>(null);

  // Team
  const [orgMembers, setOrgMembers] = useState<OrganizationMember[]>([]);
  const [assignedMembers, setAssignedMembers] = useState<AssignProjectMemberInput[]>([]);

  // Metadata
  const [projectTypes, setProjectTypes] = useState<ProjectTypeDefinition[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load project types and org members
  useEffect(() => {
    const init = async () => {
      setLoadingTypes(true);
      try {
        const types = await api.getProjectTypes();
        setProjectTypes(types || []);
      } catch (err) {
        console.error('Failed to load project types:', err);
      } finally {
        setLoadingTypes(false);
      }

      try {
        const members = await api.listMembers();
        setOrgMembers(members || []);
      } catch (err) {
        console.error('Failed to load members:', err);
      }
    };
    init();
  }, []);

  // Update default floors when project type changes
  const handleProjectTypeChange = (newType: string) => {
    setProjectType(newType);
    const def = projectTypes.find((t) => t.key === newType);
    if (def && def.default_floor_types && def.default_floor_types.length > 0) {
      const generated = def.default_floor_types.map((typeName, idx) => ({
        name: typeName,
        floor_number: idx,
        floor_type: typeName,
        area_value: 2000,
        area_unit: 'SQFT',
        height_value: 10.5,
        height_unit: 'FT',
        sequence: idx + 1,
        description: '',
      }));
      setFloors(generated);
    }
  };

  // Handle Cover Upload
  const handleCoverSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setCoverFile(file);
    setCoverPreview(URL.createObjectURL(file));

    setIsUploadingCover(true);
    try {
      const res = await api.uploadProjectCover(file);
      setCoverImageId(res.cover_image_id);
      setCoverImageUrl(res.cover_image_url);
    } catch (err: any) {
      console.error('Failed to upload cover image:', err);
      setError('Cover upload failed: ' + (err.message || 'Network error'));
    } finally {
      setIsUploadingCover(false);
    }
  };

  // Floor management
  const addFloor = () => {
    const nextNum = floors.length;
    setFloors([
      ...floors,
      {
        name: `Floor ${nextNum}`,
        floor_number: nextNum,
        floor_type: 'Typical Floor',
        area_value: 2000,
        area_unit: 'SQFT',
        height_value: 10.5,
        height_unit: 'FT',
        sequence: nextNum + 1,
        description: '',
      },
    ]);
  };

  const removeFloor = (index: number) => {
    if (floors.length <= 1) {
      alert('A project must have at least one floor or section.');
      return;
    }
    setFloors(floors.filter((_, i) => i !== index));
    const newPlans = { ...floorPlans };
    delete newPlans[index];
    setFloorPlans(newPlans);
  };

  const updateFloorField = (index: number, field: keyof CreateFloorInput, value: any) => {
    const updated = [...floors];
    updated[index] = { ...updated[index], [field]: value };
    setFloors(updated);
  };

  // Floor plan file upload
  const handleFloorPlanFileUpload = (floorIndex: number, e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setFloorPlans({
      ...floorPlans,
      [floorIndex]: {
        planType: 'UPLOADED',
        file,
        fileName: file.name,
        previewUrl: URL.createObjectURL(file),
      },
    });
  };

  // Team member toggling
  const toggleMember = (userId: string, role: string) => {
    const exists = assignedMembers.find((m) => m.user_id === userId);
    if (exists) {
      setAssignedMembers(assignedMembers.filter((m) => m.user_id !== userId));
    } else {
      setAssignedMembers([...assignedMembers, { user_id: userId, project_role: role }]);
    }
  };

  const updateMemberRole = (userId: string, role: string) => {
    setAssignedMembers(
      assignedMembers.map((m) => (m.user_id === userId ? { ...m, project_role: role } : m))
    );
  };

  // Build full payload
  const buildPayload = (status: 'ACTIVE' | 'DRAFT'): ProjectCreationFullInput => {
    return {
      name: name.trim() || 'Untitled Project',
      cover_image_id: coverImageId || undefined,
      cover_image_url: coverImageUrl || undefined,
      contact_name: contactName.trim(),
      contact_email: contactEmail.trim(),
      contact_phone: contactPhone.trim(),
      project_type: projectType,
      custom_type: customType.trim() || undefined,
      description: description.trim() || undefined,
      status,
      address,
      floors,
      members: assignedMembers,
    };
  };

  // Submit and upload floor plans
  const handleCompleteSubmission = async (isDraft: boolean = false) => {
    setError(null);

    // Basic step validation if not draft
    if (!isDraft) {
      if (!name.trim()) {
        setError('Project Name is required.');
        setCurrentStep(1);
        return;
      }
      if (!contactName.trim() || !contactPhone.trim() || !contactEmail.trim()) {
        setError('Contact Person details (Name, Phone, Email) are required.');
        setCurrentStep(2);
        return;
      }
      if (!address.address_line_1.trim() || !address.city.trim() || !address.pincode.trim()) {
        setError('Complete Address (Line 1, City, Pincode) is required.');
        setCurrentStep(3);
        return;
      }
      if (floors.length === 0) {
        setError('At least one floor or section is required.');
        setCurrentStep(4);
        return;
      }
    }

    if (isDraft) {
      setSavingDraft(true);
    } else {
      setSubmitting(true);
    }

    try {
      const payload = buildPayload(isDraft ? 'DRAFT' : 'ACTIVE');
      const project = isDraft
        ? await api.saveProjectDraft(payload)
        : await api.createProject(payload);

      // Upload attached floor plans if any
      if (project.floors && project.floors.length > 0) {
        for (let i = 0; i < project.floors.length; i++) {
          const fl = project.floors[i];
          const planDraft = floorPlans[i];
          if (!planDraft) continue;

          try {
            if (planDraft.planType === 'UPLOADED' && planDraft.file) {
              await api.uploadFloorPlan(project.id, fl.id, planDraft.file);
            } else if (planDraft.planType === 'DRAWN' && planDraft.drawingData) {
              await api.drawFloorPlan(project.id, fl.id, {
                canvas_width: 1200,
                canvas_height: 800,
                scale_ratio: 1.0,
                drawing_data: planDraft.drawingData,
                preview_base64: planDraft.drawingPreviewBase64,
              });
            }
          } catch (planErr) {
            console.warn(`Floor plan sync failed for floor ${fl.name}:`, planErr);
          }
        }
      }

      // Navigate to project dashboard
      navigate(`/projects/${project.id}`);
    } catch (err: any) {
      console.error('Project creation failed:', err);
      setError(err.message || 'Failed to initialize project');
    } finally {
      setSubmitting(false);
      setSavingDraft(false);
    }
  };

  const selectedTypeObj = projectTypes.find((t) => t.key === projectType);

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#D1C2A5] pb-5">
        <div>
          <div className="flex items-center gap-2.5 text-xs font-semibold uppercase tracking-wider text-[#8F6834]">
            <span>Project Escalation Wizard</span>
            <span>&bull;</span>
            <span>Step {currentStep} of {totalSteps}</span>
          </div>
          <h1 className="text-2xl font-bold text-[#1F150D] font-serif-brand mt-1">
            Create Physical Space Project
          </h1>
          <p className="text-xs text-[#695541] mt-0.5">
            Configure buildings, malls, halls, offices, campuses, or custom structures with real backend persistence.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleCompleteSubmission(true)}
            disabled={savingDraft || submitting}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#FAF7F2] hover:bg-[#EFE7D8] text-[#5C4D3E] border border-[#D1C2A5] rounded-xl text-xs font-semibold transition-colors shadow-xs"
          >
            {savingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            <span>Save Draft</span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="px-3.5 py-2 text-xs font-medium text-[#7C6652] hover:text-[#1F150D] transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Progress Stepper */}
      <div className="grid grid-cols-6 gap-2 bg-[#FAF7F2] p-2.5 rounded-2xl border border-[#D1C2A5] shadow-xs">
        {[
          { step: 1, title: 'Topology & Info', icon: Building2 },
          { step: 2, title: 'Contact Person', icon: Users },
          { step: 3, title: 'Address & GPS', icon: MapPin },
          { step: 4, title: 'Floors Setup', icon: Layers },
          { step: 5, title: 'Floor Plans', icon: PencilRuler },
          { step: 6, title: 'Team Assignment', icon: CheckCircle2 },
        ].map((item) => {
          const Icon = item.icon;
          const isActive = currentStep === item.step;
          const isPassed = currentStep > item.step;
          return (
            <button
              key={item.step}
              type="button"
              onClick={() => setCurrentStep(item.step)}
              className={`flex items-center gap-2 p-2 rounded-xl text-left transition-all ${
                isActive
                  ? 'bg-[#8F6834] text-[#FAF7F2] shadow-sm font-semibold'
                  : isPassed
                  ? 'bg-[#FAF3E0] text-[#8F6834] hover:bg-[#F3E7C4]'
                  : 'text-[#8C7A6B] hover:text-[#1F150D]'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <div className="hidden lg:block truncate">
                <div className="text-[10px] uppercase opacity-75">Step {item.step}</div>
                <div className="text-xs truncate">{item.title}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3 text-red-800 text-sm shadow-xs animate-shake">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-red-600" />
          <div className="flex-1">
            <span className="font-semibold">Validation Notice: </span>
            {error}
          </div>
          <button type="button" onClick={() => setError(null)} className="text-red-500 hover:text-red-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Wizard Step Content Card */}
      <div className="bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] p-6 shadow-sm space-y-6">
        {/* STEP 1: Basic Information & Topology Selection */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="border-b border-[#EAE2D3] pb-3">
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                1. Project Identity & Architectural Structure
              </h2>
              <p className="text-xs text-[#695541]">
                Define the project name, upload an architectural cover photograph, and select the structural typology.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Project Name */}
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                    Project Name <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Prestige HighLine Tech Park Tower B"
                    className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:ring-2 focus:ring-[#8F6834]/30 focus:border-[#8F6834] transition-all shadow-xs"
                  />
                </div>

                {/* Project Description */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                    Project Description (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide scope notes, architectural details, or capture objectives..."
                    className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:ring-2 focus:ring-[#8F6834]/30 focus:border-[#8F6834] transition-all shadow-xs resize-none"
                  />
                </div>

                {/* Custom Type (if Other selected) */}
                {projectType === 'Other' && (
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                      Specify Custom Structure Type <span className="text-red-600">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={customType}
                      onChange={(e) => setCustomType(e.target.value)}
                      placeholder="e.g. Heritage Temple, Underground Tunnel, Stadium"
                      className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
                    />
                  </div>
                )}
              </div>

              {/* Cover Image Upload */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                  Project Picture / Cover Photo
                </label>
                <div className="relative border-2 border-dashed border-[#D1C2A5] rounded-2xl p-4 text-center hover:border-[#8F6834] transition-colors bg-white flex flex-col items-center justify-center min-h-[200px]">
                  {coverPreview ? (
                    <div className="relative w-full h-44 rounded-xl overflow-hidden group">
                      <img src={coverPreview} alt="Cover Preview" className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <label className="cursor-pointer px-3 py-1.5 bg-[#FAF7F2] text-[#8F6834] text-xs font-bold rounded-lg shadow-sm">
                          Replace Picture
                          <input type="file" accept="image/*" className="hidden" onChange={handleCoverSelect} />
                        </label>
                      </div>
                      {isUploadingCover && (
                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center text-white text-xs gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Uploading cover...</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <label className="cursor-pointer flex flex-col items-center justify-center py-6 px-4 w-full">
                      <Upload className="w-8 h-8 text-[#8F6834] mb-2" />
                      <span className="text-xs font-semibold text-[#1F150D]">
                        Upload architectural cover photo
                      </span>
                      <span className="text-[11px] text-[#7C6652] mt-0.5">
                        PNG, JPG, JPEG or WEBP (Max 15MB)
                      </span>
                      <input type="file" accept="image/*" className="hidden" onChange={handleCoverSelect} />
                    </label>
                  )}
                </div>
              </div>
            </div>

            {/* Architectural Typology Selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#7C6652]">
                  Select Structural Typology ({projectTypes.length} Available)
                </label>
                {selectedTypeObj && (
                  <span className="text-xs text-[#8F6834] font-medium">
                    {selectedTypeObj.multi_floor ? 'Multi-Floor Structure' : 'Single Level / Hall Topology'}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5 max-h-72 overflow-y-auto pr-1">
                {projectTypes.map((t) => {
                  const isSelected = projectType === t.key;
                  return (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => handleProjectTypeChange(t.key)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'bg-[#FAF3E0] border-[#8F6834] shadow-xs'
                          : 'bg-white border-[#E0D5C1] hover:border-[#8F6834]/60'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold ${isSelected ? 'text-[#8F6834]' : 'text-[#1F150D]'}`}>
                          {t.name}
                        </span>
                        {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-[#8F6834]" />}
                      </div>
                      <p className="text-[10px] text-[#7C6652] line-clamp-2 mt-1">
                        {t.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Contact Person Details */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="border-b border-[#EAE2D3] pb-3">
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                2. Project Lead & Primary Contact
              </h2>
              <p className="text-xs text-[#695541]">
                Point of contact for site coordination, spatial scanning access, and stakeholder notifications.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                  Contact Person Name <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="e.g. Ramesh Kumar"
                  className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                  Mobile Number <span className="text-red-600">*</span>
                </label>
                <input
                  type="tel"
                  required
                  value={contactPhone}
                  onChange={(e) => setContactPhone(e.target.value)}
                  placeholder="e.g. +91 98765 43210"
                  className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652] mb-1.5">
                  Contact Email Address <span className="text-red-600">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  placeholder="e.g. ramesh.kumar@enterprise.com"
                  className="w-full px-4 py-3 bg-white border border-[#D1C2A5] rounded-xl text-sm text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:border-[#8F6834]"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Complete Project Address & Location */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="border-b border-[#EAE2D3] pb-3">
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                3. Project Physical Location & Geocoding
              </h2>
              <p className="text-xs text-[#695541]">
                Search or detect real GPS coordinates via Places API. Verify structured address components.
              </p>
            </div>

            <LocationSearchInput address={address} onChange={setAddress} />
          </div>
        )}

        {/* STEP 4: Floors & Structure Configuration */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-[#EAE2D3] pb-3">
              <div>
                <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                  4. Floor & Level Hierarchy ({floors.length} Configured)
                </h2>
                <p className="text-xs text-[#695541]">
                  Each level is an independent spatial entity with custom area, ceiling height, and floor plans.
                </p>
              </div>

              <button
                type="button"
                onClick={addFloor}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-[#FAF3E0] hover:bg-[#F3E7C4] text-[#8F6834] border border-[#D9C4A1] text-xs font-bold rounded-xl transition-colors shadow-xs"
              >
                <Plus className="w-4 h-4" />
                <span>Add Level / Floor</span>
              </button>
            </div>

            <div className="space-y-3">
              {floors.map((floor, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-white rounded-xl border border-[#D1C2A5] shadow-xs space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-[#EAE2D3] pb-2">
                    <span className="text-xs font-bold text-[#8F6834] uppercase tracking-wider">
                      Level #{idx + 1}
                    </span>
                    {floors.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeFloor(idx)}
                        className="text-red-500 hover:text-red-700 p-1 rounded-lg"
                        title="Delete Level"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-[#5C4D3E] mb-1">
                        Floor Name <span className="text-red-600">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={floor.name}
                        onChange={(e) => updateFloorField(idx, 'name', e.target.value)}
                        placeholder="e.g. Ground Floor"
                        className="w-full px-3 py-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-lg text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-[#5C4D3E] mb-1">
                        Floor Type
                      </label>
                      <input
                        type="text"
                        value={floor.floor_type}
                        onChange={(e) => updateFloorField(idx, 'floor_type', e.target.value)}
                        placeholder="e.g. Retail Deck, Lobby"
                        className="w-full px-3 py-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-lg text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-[#5C4D3E] mb-1">
                        Floor Area ({floor.area_unit}) <span className="text-red-600">*</span>
                      </label>
                      <input
                        type="number"
                        min="1"
                        required
                        value={floor.area_value}
                        onChange={(e) => updateFloorField(idx, 'area_value', parseFloat(e.target.value) || 0)}
                        placeholder="2500"
                        className="w-full px-3 py-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-lg text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-[#5C4D3E] mb-1">
                        Ceiling Height ({floor.height_unit})
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="1"
                        value={floor.height_value}
                        onChange={(e) => updateFloorField(idx, 'height_value', parseFloat(e.target.value) || 10)}
                        placeholder="10.5"
                        className="w-full px-3 py-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-lg text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 5: Floor Plans (Upload or Interactive Vector Canvas) */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div className="border-b border-[#EAE2D3] pb-3">
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                5. Floor Plan Architectural Blueprint
              </h2>
              <p className="text-xs text-[#695541]">
                Upload CAD/PDF/Image drawings OR launch the vector canvas tool to draft walls, doors, and rooms.
              </p>
            </div>

            <div className="space-y-4">
              {floors.map((floor, idx) => {
                const planDraft = floorPlans[idx];
                return (
                  <div
                    key={idx}
                    className="p-4 bg-white rounded-xl border border-[#D1C2A5] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[#1F150D]">{floor.name}</span>
                        <span className="text-[11px] text-[#7C6652]">({floor.area_value} {floor.area_unit})</span>
                      </div>
                      <div className="text-xs text-[#8F6834] font-medium mt-1">
                        {planDraft ? (
                          planDraft.planType === 'UPLOADED' ? (
                            <span>Uploaded Document: {planDraft.fileName}</span>
                          ) : (
                            <span>Vector CAD Drawing Attached ({planDraft.drawingData?.objects.length || 0} objects)</span>
                          )
                        ) : (
                          <span className="text-[#A09384]">No blueprint attached yet</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start md:self-auto">
                      {/* Upload Option */}
                      <label className="cursor-pointer flex items-center gap-1.5 px-3 py-2 bg-[#FAF7F2] hover:bg-[#EFE7D8] text-[#5C4D3E] border border-[#D1C2A5] rounded-xl text-xs font-semibold transition-colors">
                        <FileUp className="w-3.5 h-3.5" />
                        <span>Upload File</span>
                        <input
                          type="file"
                          accept=".png,.jpg,.jpeg,.pdf"
                          className="hidden"
                          onChange={(e) => handleFloorPlanFileUpload(idx, e)}
                        />
                      </label>

                      {/* Interactive Draw Option */}
                      <button
                        type="button"
                        onClick={() => setActiveDrawingFloorIndex(idx)}
                        className="flex items-center gap-1.5 px-3 py-2 bg-[#FAF3E0] hover:bg-[#F3E7C4] text-[#8F6834] border border-[#D9C4A1] rounded-xl text-xs font-bold transition-colors"
                      >
                        <PencilRuler className="w-3.5 h-3.5" />
                        <span>Draw Vector Plan</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 6: Team Member Assignment & Final Review */}
        {currentStep === 6 && (
          <div className="space-y-6">
            <div className="border-b border-[#EAE2D3] pb-3">
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                6. Project Team Assignment & Final Launch
              </h2>
              <p className="text-xs text-[#695541]">
                Assign organization colleagues to this project with role-based permissions.
              </p>
            </div>

            {/* Member list */}
            <div className="space-y-3">
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#7C6652]">
                Assign Organization Members ({assignedMembers.length} Selected)
              </label>

              {orgMembers.length === 0 ? (
                <div className="p-4 bg-white rounded-xl border border-[#D1C2A5] text-xs text-[#7C6652]">
                  No other organization members found. You will be assigned as Project Admin.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto pr-1">
                  {orgMembers.map((m) => {
                    const assigned = assignedMembers.find((a) => a.user_id === m.user_id);
                    return (
                      <div
                        key={m.id}
                        className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                          assigned
                            ? 'bg-[#FAF3E0] border-[#8F6834]'
                            : 'bg-white border-[#E0D5C1]'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <div className="text-xs font-bold text-[#1F150D] truncate">
                            {m.user?.full_name || m.user_name || m.user_email}
                          </div>
                          <div className="text-[11px] text-[#7C6652] truncate">{m.user?.email || m.user_email}</div>
                        </div>

                        <div className="flex items-center gap-2">
                          {assigned ? (
                            <>
                              <select
                                value={assigned.project_role}
                                onChange={(e) => updateMemberRole(m.user_id, e.target.value)}
                                className="px-2 py-1 bg-white border border-[#D1C2A5] rounded-lg text-xs text-[#1F150D]"
                              >
                                <option value="Project Manager">Project Manager</option>
                                <option value="Site Manager">Site Manager</option>
                                <option value="Surveyor">Surveyor</option>
                                <option value="Architect">Architect</option>
                                <option value="Engineer">Engineer</option>
                                <option value="Supervisor">Supervisor</option>
                                <option value="Field Executive">Field Executive</option>
                                <option value="Viewer">Viewer</option>
                              </select>
                              <button
                                type="button"
                                onClick={() => toggleMember(m.user_id, 'Viewer')}
                                className="text-xs text-red-600 hover:underline"
                              >
                                Remove
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => toggleMember(m.user_id, 'Project Manager')}
                              className="px-2.5 py-1 bg-[#FAF7F2] hover:bg-[#EFE7D8] text-[#8F6834] border border-[#D1C2A5] rounded-lg text-xs font-semibold"
                            >
                              Assign
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Summary Review Card */}
            <div className="p-4 bg-[#FAF3E0] rounded-xl border border-[#D9C4A1] space-y-2 text-xs text-[#5C4D3E]">
              <div className="font-bold text-[#8F6834] uppercase tracking-wider text-[11px]">
                Project Launch Overview
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                <div>
                  <span className="text-[#8C7A6B]">Project:</span> {name || 'Untitled'}
                </div>
                <div>
                  <span className="text-[#8C7A6B]">Type:</span> {projectType}
                </div>
                <div>
                  <span className="text-[#8C7A6B]">Levels:</span> {floors.length} Floors
                </div>
                <div>
                  <span className="text-[#8C7A6B]">Location:</span> {address.city || 'Unset'}, {address.state}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Footer Controls */}
        <div className="flex items-center justify-between border-t border-[#EAE2D3] pt-5">
          <button
            type="button"
            disabled={currentStep === 1}
            onClick={() => setCurrentStep((s) => Math.max(1, s - 1))}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-[#FAF7F2] border border-[#D1C2A5] hover:bg-[#EFE7D8] text-[#5C4D3E] text-xs font-semibold rounded-xl transition-colors disabled:opacity-40"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Previous Step</span>
          </button>

          <div className="flex items-center gap-2">
            {currentStep < totalSteps ? (
              <button
                type="button"
                onClick={() => setCurrentStep((s) => Math.min(totalSteps, s + 1))}
                className="flex items-center gap-1.5 px-5 py-2.5 bg-[#8F6834] hover:bg-[#755427] text-[#FAF7F2] text-xs font-bold rounded-xl shadow-sm transition-all"
              >
                <span>Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => handleCompleteSubmission(false)}
                disabled={submitting}
                className="flex items-center gap-1.5 px-6 py-2.5 bg-[#8F6834] hover:bg-[#755427] text-[#FAF7F2] text-xs font-bold rounded-xl shadow-md transition-all disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Creating Spatial Project...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Create & Publish Project</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Vector Canvas Drawer Modal */}
      {activeDrawingFloorIndex !== null && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-6xl h-[85vh]">
            <FloorPlanDrawer
              initialData={floorPlans[activeDrawingFloorIndex]?.drawingData}
              onCancel={() => setActiveDrawingFloorIndex(null)}
              onSave={(result) => {
                setFloorPlans({
                  ...floorPlans,
                  [activeDrawingFloorIndex]: {
                    planType: 'DRAWN',
                    drawingData: result.drawing_data,
                    drawingPreviewBase64: result.preview_base64,
                    fileName: `Vector_Blueprint_${floors[activeDrawingFloorIndex].name}.cad`,
                  },
                });
                setActiveDrawingFloorIndex(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
