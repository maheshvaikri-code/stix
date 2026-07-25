/** @type {import('next').NextConfig} */
const useStandaloneOutput = process.env.NEXT_OUTPUT_STANDALONE === 'true';

const nextConfig = {
  ...(useStandaloneOutput ? { output: 'standalone' } : {}),
  serverExternalPackages: [],
};

module.exports = nextConfig;
