// Google Identity Services (GIS) Client Integration
const GOOGLE_CLIENT_ID =
  (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
  '844723010661-l48463a33i9t1a3pelk6hbhhh0d5htgv.apps.googleusercontent.com';

declare global {
  interface Window {
    google?: any;
  }
}

/**
 * Dynamically loads Google Identity Services SDK
 */
export function loadGoogleSDK(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') return resolve();
    if (window.google?.accounts?.id || window.google?.accounts?.oauth2) return resolve();

    const existing = document.getElementById('google-gsi-script');
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => resolve());
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      reject(new Error('Failed to load Google Identity Services SDK'));
    };
    document.head.appendChild(script);
  });
}

/**
 * Triggers Google Sign-In Popup & returns verified Google ID / access token
 */
export async function triggerGoogleSignIn(): Promise<string> {
  await loadGoogleSDK();

  return new Promise((resolve, reject) => {
    if (!window.google?.accounts) {
      return reject(new Error('Google Identity Services SDK not available'));
    }

    let completed = false;

    // 1. Try OAuth2 token client popup
    if (window.google.accounts.oauth2) {
      try {
        const tokenClient = window.google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: 'openid email profile',
          prompt: 'select_account',
          callback: async (tokenResponse: any) => {
            if (tokenResponse.error) {
              return reject(new Error(`Google Sign-In error: ${tokenResponse.error}`));
            }

            if (tokenResponse.access_token) {
              completed = true;
              return resolve(tokenResponse.access_token);
            }
            return reject(new Error('No access token received from Google'));
          },
        });

        tokenClient.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (e) {
        console.warn('OAuth2 token client initialization error', e);
      }
    }

    // 2. Try GSI One-Tap / Credential prompt
    if (window.google.accounts.id) {
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response: any) => {
            if (response.credential) {
              completed = true;
              resolve(response.credential);
            } else {
              reject(new Error('No credentials returned from Google'));
            }
          },
          auto_select: false,
          cancel_on_tap_outside: false,
        });

        window.google.accounts.id.prompt((notification: any) => {
          if (!completed && (notification.isNotDisplayed() || notification.isSkippedMoment())) {
            reject(new Error('Google Sign-In prompt was suppressed or dismissed'));
          }
        });
        return;
      } catch (e) {
        return reject(new Error(`Google Identity initialization failed: ${e}`));
      }
    }

    reject(new Error('Google Sign-In authentication method unavailable'));
  });
}
