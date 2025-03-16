/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Only rewrite specific endpoints that exist in the backend
      {
        source: '/api/upload',
        destination: 'http://localhost:8000/upload',
      },
      {
        source: '/api/status/:path*',
        destination: 'http://localhost:8000/status/:path*',
      },
      {
        source: '/api/reprocess/:path*',
        destination: 'http://localhost:8000/reprocess/:path*',
      },
      {
        source: '/api/use-sample',
        destination: 'http://localhost:8000/use-sample',
      },
      {
        source: '/api/sample.wav',
        destination: 'http://localhost:8000/sample.wav',
      }
    ];
  },
};

module.exports = nextConfig; 