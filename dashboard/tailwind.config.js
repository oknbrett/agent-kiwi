/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#060607',
        panel: '#0b0c0e',
        card: '#101114',
        raise: '#16181c',
        line: '#1e2126',
        'line-2': '#2b2f36',
        t1: '#eceef2',
        t2: '#9ba0ab',
        t3: '#5d626c',
        kiwi: '#b5e84d',
        esc: '#ff5d5d',
        'esc-dim': '#3a1416',
        mon: '#f0a93c',
        'mon-dim': '#332108',
        ok: '#46c98c',
        'ok-dim': '#0d291c',
        qt: '#565b66',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['"Archivo"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      transitionTimingFunction: {
        out: 'cubic-bezier(0.25, 1, 0.5, 1)',
      },
    },
  },
  plugins: [],
};
