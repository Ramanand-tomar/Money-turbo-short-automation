/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        border: "hsl(var(--border))",
        accent: {
          gold: "#ffd700",
          "gold-hover": "#ffc800",
          green: "#10b981",
          red: "#ef4444",
          blue: "#3b82f6",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Outfit", "sans-serif"],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2.5s infinite ease-in-out',
        'spin-slow': 'spin 8s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': {
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3), 0 0 10px rgba(59, 130, 246, 0.2)',
          },
          '50%': {
            boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.3), 0 0 25px rgba(59, 130, 246, 0.65)',
            borderColor: '#60a5fa',
          },
        },
      },
    },
  },
  plugins: [],
}
