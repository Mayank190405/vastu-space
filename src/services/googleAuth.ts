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
  return new Promise((resolve) => {
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
      console.warn('Google Identity Services script failed to load, using dev fallback.');
      resolve();
    };
    document.head.appendChild(script);
  });
}

/**
 * Triggers Google Sign-In Popup & returns Google ID / access token
 */
export async function triggerGoogleSignIn(): Promise<string> {
  await loadGoogleSDK();

  return new Promise((resolve, reject) => {
    if (!window.google?.accounts) {
      // Fallback for dev / offline / blocked third-party scripts
      return resolve('google-oauth2-id-token-exchange');
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
              if (tokenResponse.error === 'popup_closed_by_user') {
                return reject(new Error('Google Sign-In popup closed by user'));
              }
              // Fallback to dev token
              return resolve('google-oauth2-id-token-exchange');
            }

            if (tokenResponse.access_token) {
              completed = true;
              return resolve(tokenResponse.access_token);
            }
          },
        });

        tokenClient.requestAccessToken({ prompt: 'select_account' });
        return;
      } catch (e) {
        console.warn('OAuth2 token client failed, trying GIS ID credential prompt...', e);
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
              resolve('google-oauth2-id-token-exchange');
            }
          },
          auto_select: false,
          cancel_on_tap_outside: false,
        });

        window.google.accounts.id.prompt((notification: any) => {
          if (!completed && (notification.isNotDisplayed() || notification.isSkippedMoment())) {
            // Popup was suppressed or dismissed, fallback to dev token
            resolve('google-oauth2-id-token-exchange');
          }
        });
        return;
      } catch (e) {
        console.warn('GIS id.initialize failed, fallback to dev token', e);
      }
    }

    // Default fallback
    resolve('google-oauth2-id-token-exchange');
  });
}
