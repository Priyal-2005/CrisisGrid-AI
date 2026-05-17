import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0A0C10",
        foreground: "#FFFFFF",
        surface: "#12151C",
        border: "#1E2D4A",
        primary: "#00D4FF",
        critical: "#FF2D55",
        high: "#FF6B35",
        medium: "#FF9500",
        low: "#30D158",
        muted: "#8E9BB5",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
