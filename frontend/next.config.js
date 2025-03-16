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
    ];
  },
};

module.exports = nextConfig; 