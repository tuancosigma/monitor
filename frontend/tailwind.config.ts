import type { Config } from "tailwindcss";

// Sentinel "Operator's Console" design tokens.
// Two deliberate, anti-generic choices baked in at the token layer so every
// page inherits them without per-file churn:
//   1. The `slate` scale is re-tinted to WARM NEUTRAL (zinc) — removes the
//      blue-grey "AI dashboard" cast while existing `slate-*` classes keep working.
//   2. Brand accent is a restrained AMBER/GOLD (a watchful beacon — fits "Sentinel"),
//      not the default sky-blue. Semantic severity colors are untouched.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        // Warm-neutral re-tint of the slate scale (zinc values).
        slate: {
          50: "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#161618",
          950: "#0a0a0b",
        },
        // Brand accent — amber/gold, used sparingly (logo, active nav, CTAs, focus).
        accent: {
          DEFAULT: "#f59e0b", // amber-500
          soft: "#fbbf24", // amber-400
          deep: "#b45309", // amber-700
        },
        line: "rgba(255,255,255,0.08)", // hairline border
        surface: {
          DEFAULT: "rgba(255,255,255,0.025)", // translucent panel
          muted: "#0a0a0b",
          raised: "rgba(255,255,255,0.05)",
        },
        // Status semantics
        ok: "#34d399",
        warn: "#fbbf24",
        danger: "#f87171",
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: {
        card: "0.875rem", // 14px
      },
      boxShadow: {
        glow: "0 0 24px -6px rgba(245,158,11,0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
