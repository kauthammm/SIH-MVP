/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        kv: {
          forest: '#1b4332',
          forestDark: '#081c15',
          sage: '#40916c',
          sageLight: '#d8f3dc',
          sageMuted: '#b7e4c7',
          cream: '#faf7f2',
          creamDark: '#f0ebe3',
          beige: '#ede8df',
          gold: '#d4a373',
          wheat: '#faedcd',
        },
      },
      boxShadow: {
        hero: '0 8px 40px rgba(27, 67, 50, 0.12)',
        card: '0 2px 12px rgba(0,0,0,0.06)',
        input: '0 4px 24px rgba(0,0,0,0.08)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
    },
  },
  plugins: [],
}
