const BASE_URL = import.meta.env.VITE_GATEWAY_BASE_URL || 'http://localhost:8080';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  email_verified: boolean;
  plan_type: 'free' | 'pro' | 'partner';
  trial_end_at: string | null;
  created_at: string;
}

export interface AuthResponse {
  user: UserProfile;
  tokens: AuthTokens;
}

export interface MeResponse {
  user: UserProfile;
  trial_left_days: number | null;
  is_trial_active: boolean;
}

class AuthService {
  async registerWithEmail(email: string, password: string): Promise<AuthResponse> {
    const response = await fetch(`${BASE_URL}/auth/email/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return response.json();
  }

  async loginWithEmail(email: string, password: string): Promise<AuthResponse> {
    const response = await fetch(`${BASE_URL}/auth/email/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  getGoogleAuthUrl(): string {
    return `${BASE_URL}/auth/google/start`;
  }

  async handleGoogleCallback(code: string): Promise<AuthResponse> {
    const response = await fetch(`${BASE_URL}/auth/google/callback?code=${code}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Google authentication failed');
    }

    return response.json();
  }

  async refreshAccessToken(refreshToken: string): Promise<{ access_token: string }> {
    const response = await fetch(`${BASE_URL}/auth/token/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    return response.json();
  }

  async logout(refreshToken: string): Promise<void> {
    await fetch(`${BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getMe(accessToken: string): Promise<MeResponse> {
    const response = await fetch(`${BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch user profile');
    }

    return response.json();
  }
}

export const authService = new AuthService();
