import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        stix: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          900: "#083344",
          ink: "#07111f",
          mist: "#eef4f8",
        },
      },
      boxShadow: {
        premium: "0 24px 80px rgba(15, 23, 42, 0.14)",
        glow: "0 0 40px rgba(34, 211, 238, 0.28)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
};

export default config;
