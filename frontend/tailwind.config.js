/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // 60-30-10 palette
        brand: {
          primary: '#1D4ED8',   // Blue 700 - trust (30%)
          secondary: '#0F172A', // Slate 900 - headers/footer
          accent: '#F59E0B',    // Amber 500 - CTAs (10%)
          neutral: '#F8FAFC'    // Slate 50 - background (60%)
        }
      }
    }
  },
  plugins: []
}
