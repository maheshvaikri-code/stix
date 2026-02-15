/** @type {import('next').NextConfig} */
const useStandaloneOutput = process.env.NEXT_OUTPUT_STANDALONE === 'true';

const nextConfig = {
  ...(useStandaloneOutput ? { output: 'standalone' } : {}),
  experimental: {
    serverComponentsExternalPackages: [],
  },
};

module.exports = nextConfig;
