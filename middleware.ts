import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware: Kontrol akses /admin berdasarkan environment variable.
 *
 * Cara kerja di Railway:
 *   - Service frontend-user  → ENABLE_ADMIN=false → /admin di-redirect ke /
 *   - Service frontend-admin → ENABLE_ADMIN=true  → /admin bisa diakses
 *
 * Cara kerja di lokal:
 *   - npm run dev         → ENABLE_ADMIN tidak di-set → /admin BISA diakses (dev mode)
 *   - npm run dev:admin   → ENABLE_ADMIN=true → /admin bisa diakses
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Hanya intercept route /admin/*
  if (!pathname.startsWith('/admin')) {
    return NextResponse.next();
  }

  // Cek env var ENABLE_ADMIN
  const enableAdmin = process.env.ENABLE_ADMIN;

  // Jika ENABLE_ADMIN === 'false' → block akses admin, redirect ke home
  if (enableAdmin === 'false') {
    const homeUrl = request.nextUrl.clone();
    homeUrl.pathname = '/';
    return NextResponse.redirect(homeUrl);
  }

  // Default: izinkan akses (untuk development dan admin service)
  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*'],
};
