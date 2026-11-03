// Optional password for the hosted site (Vercel Routing Middleware, works on the free Hobby plan).
// Set SITE_PASSWORD (and optionally SITE_USER) in Vercel -> Project -> Settings -> Environment Variables,
// then redeploy. Without SITE_PASSWORD the site is open to anyone with the link.
export const config = { matcher: '/:path*' };

export default function middleware(request) {
  const password = process.env.SITE_PASSWORD;
  if (!password) return;                       // no password set: serve the page
  const user = process.env.SITE_USER || 'me';
  const header = request.headers.get('authorization') || '';
  if (header.startsWith('Basic ')) {
    const [u, p] = atob(header.slice(6)).split(':');
    if (u === user && p === password) return;   // continue to the static page
  }
  return new Response('Authentication required', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="Signals", charset="UTF-8"' },
  });
}
