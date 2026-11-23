/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F4EF",
        stone: {
          surface: "#E5DFD5",
          border: "#D6CFBF",
        },
        ink: "#141413",
        graphite: "#52504A",
        vermilion: {
          DEFAULT: "#E85D2A",
          dark: "#C7481A",
          light: "#FA723F",
        },
        cyanBadge: "#00D4E5",
        forest: {
          DEFAULT: "#154734",
          light: "#1B5E45",
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'brutal-sm': '2px 2px 0px #141413',
        'brutal': '3px 3px 0px #141413',
        'brutal-lg': '4px 4px 0px #141413',
      },
    },
  },
  plugins: [],
}
