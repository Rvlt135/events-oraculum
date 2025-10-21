import { http, HttpResponse } from 'msw';

const BASE_URL = import.meta.env.VITE_GATEWAY_BASE_URL || 'http://localhost:8080';

const mockUser = {
  id: 'uuid-mock-user-123',
  email: 'user@example.com',
  email_verified: true,
  plan_type: 'free',
  trial_end_at: '2025-12-31T00:00:00Z',
  created_at: '2025-01-01T00:00:00Z',
};

const mockTokens = {
  access_token: 'mock_access_token_xyz',
  refresh_token: 'mock_refresh_token_abc',
  token_type: 'bearer',
};

export const handlers = [
  http.post(`${BASE_URL}/auth/email/register`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    return HttpResponse.json({
      user: { ...mockUser, email: body.email },
      tokens: mockTokens,
    });
  }),

  http.post(`${BASE_URL}/auth/email/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    return HttpResponse.json({
      user: { ...mockUser, email: body.email },
      tokens: mockTokens,
    });
  }),

  http.get(`${BASE_URL}/auth/google/start`, () => {
    return HttpResponse.json(
      { redirect_to: `${BASE_URL}/auth/google/callback?code=mock_google_code` },
      { status: 302 }
    );
  }),

  http.get(`${BASE_URL}/auth/google/callback`, ({ request }) => {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');

    if (code) {
      return HttpResponse.json({
        user: { ...mockUser, email: 'google.user@example.com', email_verified: true },
        tokens: mockTokens,
      });
    }

    return HttpResponse.json({ error: 'Invalid code' }, { status: 400 });
  }),

  http.post(`${BASE_URL}/auth/token/refresh`, async ({ request }) => {
    const body = await request.json() as { refresh_token: string };

    if (body.refresh_token) {
      return HttpResponse.json({
        access_token: 'mock_access_token_refreshed',
        token_type: 'bearer',
      });
    }

    return HttpResponse.json({ error: 'Invalid refresh token' }, { status: 401 });
  }),

  http.post(`${BASE_URL}/auth/logout`, async () => {
    return HttpResponse.json({ ok: true });
  }),

  http.get(`${BASE_URL}/auth/me`, ({ request }) => {
    const authHeader = request.headers.get('Authorization');

    if (authHeader && authHeader.startsWith('Bearer ')) {
      return HttpResponse.json({
        user: mockUser,
        trial_left_days: 5,
        is_trial_active: true,
      });
    }

    return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }),
];
