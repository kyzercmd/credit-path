import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/contexts/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        secondary: "var(--secondary)",
        border: "var(--border)",
        outer: "var(--outer-bg)",
        accent: {
          DEFAULT: "var(--accent)",
          soft: "var(--accent-soft)",
          text: "var(--accent-text)",
        },
        status: {
          green: "var(--status-green)",
          "green-bg": "var(--status-green-bg)",
          amber: "var(--status-amber)",
          "amber-bg": "var(--status-amber-bg)",
          red: "var(--status-red)",
          "red-bg": "var(--status-red-bg)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "var(--font-noto-bengali)", "system-ui", "sans-serif"],
        bengali: ["var(--font-noto-bengali)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
