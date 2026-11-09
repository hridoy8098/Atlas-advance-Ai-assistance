/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        atlas: {
          cyan: '#00ffc8',
          dark: '#000d0a',
          panel: 'rgba(0,20,16,0.82)',
          border: 'rgba(0,255,200,0.25)',
        }
      },
      fontFamily: {
        orbitron: ['Orbitron', 'monospace'],
        mono: ['Share Tech Mono', 'monospace'],
        rajdhani: ['Rajdhani', 'sans-serif'],
      }
    }
  },
  plugins: []
}
