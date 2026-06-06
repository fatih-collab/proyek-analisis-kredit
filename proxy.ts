import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Proxy: Block /admin routes on port 3000.
 * Admin panel hanya bisa diakses via port 3001 (npm run dev:admin).
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const host = request.headers.get('host') || '';

  // Jika request ke /admin/* dan bukan dari port 3001 → redirect ke home
  if (pathname.startsWith('/admin')) {
    // Izinkan jika dari port 3001
    if (host.includes('3001')) {
      return NextResponse.next();
    }
    // Block dari port 3000 atau port lain → redirect ke home
    const homeUrl = request.nextUrl.clone();
    homeUrl.pathname = '/';
    return NextResponse.redirect(homeUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*'],
};
