import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/auth/LoginPage';
import { OrganizationSignupPage } from './pages/auth/OrganizationSignupPage';
import { EmployeeJoinPage } from './pages/auth/EmployeeJoinPage';
import { PendingApprovalPage } from './pages/auth/PendingApprovalPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { ProjectsPage } from './pages/projects/ProjectsPage';
import { ProjectCreationWizard } from './pages/projects/ProjectCreationWizard';
import { ProjectPipelinePage } from './pages/projects/ProjectPipelinePage';
import { ProjectDashboardPage } from './pages/projects/ProjectDashboardPage';
import { OrganizationManagementPage } from './pages/organization/OrganizationManagementPage';
import { OrganizationMembersPage } from './pages/organization/OrganizationMembersPage';
import { OrganizationRequestsPage } from './pages/organization/OrganizationRequestsPage';
import { SettingsPage } from './pages/settings/SettingsPage';
import { SpatialViewerPage } from './pages/viewer/SpatialViewerPage';
import { ProjectViewingPage } from './pages/viewer/ProjectViewingPage';
import { ARNavigationPage } from './pages/viewer/ARNavigationPage';
import { GuidedCaptureStudioPage } from './pages/capture/GuidedCaptureStudioPage';
import { CapturesPage } from './pages/capture/CapturesPage';
import { AssetsPage } from './pages/assets/AssetsPage';
import { FloorPlanStudioPage } from './pages/cad/FloorPlanStudioPage';
import { PipelineCommandCenterPage } from './pages/pipeline/PipelineCommandCenterPage';
import { VirtualTourStudioPage } from './pages/tours/VirtualTourStudioPage';
import { ReconstructionTrackingPage } from './pages/dashboard/ReconstructionTrackingPage';
import { SessionDetailPage } from './pages/dashboard/SessionDetailPage';
import { SessionListPage } from './pages/dashboard/SessionListPage';
import { DeviceMonitoringPage } from './pages/dashboard/DeviceMonitoringPage';
import { RoomMappingPage } from './pages/dashboard/RoomMappingPage';
import { ProjectWebsitePage } from './pages/website/ProjectWebsitePage';
import { LiveDigitalTwinOutputPage } from './pages/viewer/LiveDigitalTwinOutputPage';


// Root gatekeeper: Shows project website for public visitors, or routes authenticated users directly to console
const RootResolver: React.FC = () => {
  const { user, isLoading, hasActiveOrg, hasPendingJoin } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#E3DACA] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#C5A059] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <ProjectWebsitePage />;
  }

  if (hasActiveOrg) {
    return <Navigate to="/dashboard" replace />;
  }

  if (hasPendingJoin) {
    return <Navigate to="/pending-approval" replace />;
  }

  return <Navigate to="/signup/organization" replace />;
};

// Protected Route Wrapper with AppLayout
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading, hasActiveOrg, hasPendingJoin } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#E3DACA] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#C5A059] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  if (hasPendingJoin) {
    return <Navigate to="/pending-approval" replace />;
  }

  if (!hasActiveOrg) {
    return <Navigate to="/signup/organization" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Root Landing Page: Dedicated Project Website */}
          <Route path="/" element={<ProjectWebsitePage />} />

          {/* Dedicated Project Website & Architecture Portal */}
          <Route path="/website" element={<ProjectWebsitePage />} />
          <Route path="/website/platform" element={<ProjectWebsitePage />} />
          <Route path="/website/approach" element={<ProjectWebsitePage />} />
          <Route path="/website/guide" element={<ProjectWebsitePage />} />
          <Route path="/overview" element={<ProjectWebsitePage />} />
          <Route path="/about" element={<ProjectWebsitePage />} />
          <Route path="/guide" element={<ProjectWebsitePage />} />
          <Route path="/project" element={<ProjectWebsitePage />} />

          {/* Public 3D Spatial Viewer & Demo Routes */}
          <Route path="/output" element={<LiveDigitalTwinOutputPage />} />
          <Route path="/twin" element={<LiveDigitalTwinOutputPage />} />
          <Route path="/viewer" element={<div className="min-h-screen bg-[#E3DACA] p-6"><SpatialViewerPage /></div>} />
          <Route path="/3d" element={<div className="min-h-screen bg-[#E3DACA] p-6"><SpatialViewerPage /></div>} />
          <Route path="/ar" element={<ARNavigationPage />} />
          <Route path="/viewer/ar" element={<ARNavigationPage />} />
          {/* Public Project 3D Digital Twin Viewing Link */}
          <Route path="/view/:projectId" element={<ProjectViewingPage />} />
          {/* Direct Mobile Surveyor Link */}
          <Route path="/capture/:captureId" element={<GuidedCaptureStudioPage />} />

          {/* Public Auth & Onboarding Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<LoginPage />} />
          <Route path="/signup" element={<OrganizationSignupPage />} />
          <Route path="/signup/organization" element={<OrganizationSignupPage />} />
          <Route path="/onboarding/organization" element={<OrganizationSignupPage />} />
          <Route path="/join" element={<EmployeeJoinPage />} />
          <Route path="/join/:orgCode" element={<EmployeeJoinPage />} />
          <Route path="/join/:orgCode/:inviteToken" element={<EmployeeJoinPage />} />
          <Route path="/pending-approval" element={<PendingApprovalPage />} />

          {/* Protected Multi-Page Workspace Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects"
            element={
              <ProtectedRoute>
                <ProjectsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/captures"
            element={
              <ProtectedRoute>
                <CapturesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assets"
            element={
              <ProtectedRoute>
                <AssetsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cad"
            element={
              <ProtectedRoute>
                <FloorPlanStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/floorplan"
            element={
              <ProtectedRoute>
                <FloorPlanStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/pipeline"
            element={
              <ProtectedRoute>
                <PipelineCommandCenterPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/tours"
            element={
              <ProtectedRoute>
                <VirtualTourStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/presentation"
            element={
              <ProtectedRoute>
                <VirtualTourStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/activity"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/search"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/create"
            element={
              <ProtectedRoute>
                <ProjectCreationWizard />
              </ProtectedRoute>
            }
          />
          <Route path="/projects/:projectId/pipelines" element={<ProtectedRoute><ProjectPipelinePage /></ProtectedRoute>} />
          <Route path="/projects/:projectId/pipelines/:sessionId" element={<ProtectedRoute><ReconstructionTrackingPage /></ProtectedRoute>} />
          <Route
            path="/projects/:projectId"
            element={
              <ProtectedRoute>
                <ProjectDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/viewer"
            element={
              <ProtectedRoute>
                <ProjectViewingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/capture/:captureId"
            element={
              <ProtectedRoute>
                <GuidedCaptureStudioPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/team"
            element={
              <ProtectedRoute>
                <OrganizationMembersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization"
            element={
              <ProtectedRoute>
                <OrganizationManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization/members"
            element={
              <ProtectedRoute>
                <OrganizationMembersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/organization/requests"
            element={
              <ProtectedRoute>
                <OrganizationRequestsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />

          {/* Phase 7 Admin Dashboard & Real-Time Session Routes */}
          <Route
            path="/dashboard/projects"
            element={
              <ProtectedRoute>
                <ProjectsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/projects/new"
            element={
              <ProtectedRoute>
                <ProjectCreationWizard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/projects/:projectId"
            element={
              <ProtectedRoute>
                <ProjectDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/projects/:projectId/rooms"
            element={
              <ProtectedRoute>
                <RoomMappingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/sessions"
            element={
              <ProtectedRoute>
                <SessionListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/sessions/:sessionId"
            element={
              <ProtectedRoute>
                <SessionDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/devices"
            element={
              <ProtectedRoute>
                <DeviceMonitoringPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/reconstruction/:sessionId"
            element={
              <ProtectedRoute>
                <ReconstructionTrackingPage />
              </ProtectedRoute>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};
