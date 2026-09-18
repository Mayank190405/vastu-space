import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, Organization, OrganizationMember } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  activeOrg: Organization | null;
  activeRole: string | null;
  memberships: OrganizationMember[];
  isLoading: boolean;
  error: string | null;
  hasActiveOrg: boolean;
  hasPendingJoin: boolean;
  setSession: (data: {
    user: User;
    tokens: { access_token: string; refresh_token: string };
    activeOrg?: Organization;
    memberships?: OrganizationMember[];
    activeRole?: string;
  }) => void;
  updateActiveOrg: (org: Organization) => void;
  switchOrganization: (orgId: string) => void;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const getStoredItem = <T,>(key: string): T | null => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  } catch {
    return null;
  }
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Synchronously hydrate state from localStorage for instantaneous rendering without layout shift
  const [user, setUser] = useState<User | null>(() => getStoredItem<User>('vastu_user'));
  const [activeOrg, setActiveOrg] = useState<Organization | null>(() => getStoredItem<Organization>('vastu_active_org'));
  const [activeRole, setActiveRole] = useState<string | null>(() => localStorage.getItem('vastu_active_role'));
  const [memberships, setMemberships] = useState<OrganizationMember[]>(() => getStoredItem<OrganizationMember[]>('vastu_memberships') || []);
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    const token = localStorage.getItem('vastu_access_token');
    const storedUser = localStorage.getItem('vastu_user');
    // If there is no token, unauthenticated state is immediately resolved with no spinner
    if (!token) return false;
    // If token exists but user is not cached in localStorage, wait for /auth/me
    return !storedUser;
  });
  const [error, setError] = useState<string | null>(null);

  const loadSession = async () => {
    const token = localStorage.getItem('vastu_access_token');
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      setError(null);
      const res = await api.getMe();
      setUser(res.user);
      setActiveOrg(res.active_org || null);
      setActiveRole(res.active_role || null);
      setMemberships(res.memberships || []);

      // Persist hydrated state
      localStorage.setItem('vastu_user', JSON.stringify(res.user));
      if (res.active_org) {
        localStorage.setItem('vastu_active_org', JSON.stringify(res.active_org));
      } else {
        localStorage.removeItem('vastu_active_org');
      }
      if (res.active_role) {
        localStorage.setItem('vastu_active_role', res.active_role);
      }
      if (res.memberships) {
        localStorage.setItem('vastu_memberships', JSON.stringify(res.memberships));
      }
    } catch (err: any) {
      console.warn('Session verification error, attempting refresh:', err);
      const refreshed = await api.refreshToken();
      if (refreshed) {
        try {
          const res = await api.getMe();
          setUser(res.user);
          setActiveOrg(res.active_org || null);
          setActiveRole(res.active_role || null);
          setMemberships(res.memberships || []);
          return;
        } catch {
          // fall through
        }
      }
      // If refresh failed, clear invalid session
      clearStoredSession();
      setUser(null);
      setActiveOrg(null);
      setActiveRole(null);
      setMemberships([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSession();

    // Background token refresh interval (every 4 minutes)
    const interval = setInterval(() => {
      const refreshToken = localStorage.getItem('vastu_refresh_token');
      if (refreshToken) {
        api.refreshToken().catch(() => {});
      }
    }, 4 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const clearStoredSession = () => {
    localStorage.removeItem('vastu_access_token');
    localStorage.removeItem('vastu_refresh_token');
    localStorage.removeItem('vastu_user');
    localStorage.removeItem('vastu_active_org');
    localStorage.removeItem('vastu_active_role');
    localStorage.removeItem('vastu_memberships');
  };

  const setSession = (data: {
    user: User;
    tokens: { access_token: string; refresh_token: string };
    activeOrg?: Organization;
    memberships?: OrganizationMember[];
    activeRole?: string;
  }) => {
    localStorage.setItem('vastu_access_token', data.tokens.access_token);
    localStorage.setItem('vastu_refresh_token', data.tokens.refresh_token);
    localStorage.setItem('vastu_user', JSON.stringify(data.user));
    setUser(data.user);

    if (data.activeOrg) {
      localStorage.setItem('vastu_active_org', JSON.stringify(data.activeOrg));
      setActiveOrg(data.activeOrg);
    }
    if (data.activeRole) {
      localStorage.setItem('vastu_active_role', data.activeRole);
      setActiveRole(data.activeRole);
    }
    if (data.memberships) {
      localStorage.setItem('vastu_memberships', JSON.stringify(data.memberships));
      setMemberships(data.memberships);
    }
    setIsLoading(false);
  };

  const updateActiveOrg = (org: Organization) => {
    setActiveOrg(org);
    localStorage.setItem('vastu_active_org', JSON.stringify(org));
  };

  const switchOrganization = (orgId: string) => {
    const target = memberships.find((m) => m.org_id === orgId && m.status === 'active');
    if (target) {
      const org: Organization = target.organization || {
        id: target.org_id,
        name: target.org_name || 'Workspace',
        org_code: target.org_code || '',
        status: 'active',
        created_at: target.created_at,
      };
      setActiveOrg(org);
      setActiveRole(target.role);
      localStorage.setItem('vastu_active_org', JSON.stringify(org));
      localStorage.setItem('vastu_active_role', target.role);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      clearStoredSession();
      setUser(null);
      setActiveOrg(null);
      setActiveRole(null);
      setMemberships([]);
      window.location.href = '/login';
    }
  };

  const hasActiveOrg = Boolean(activeOrg && activeOrg.id);
  const hasPendingJoin = Boolean(!hasActiveOrg && memberships.some(m => m.status === 'invited'));

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        activeRole,
        memberships,
        isLoading,
        error,
        hasActiveOrg,
        hasPendingJoin,
        setSession,
        updateActiveOrg,
        switchOrganization,
        logout,
        refreshProfile: loadSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
