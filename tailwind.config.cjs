/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './index.html',
    './script.js',
    './site-enhancements.js',
    './validation-tracker.js',
    './fragrantica-image-link.js'
  ],
  safelist: [
    'hidden',
    'rotate-180',
    'bg-red-800',
    'bg-emerald-800'
  ],
  theme: {
    extend: {}
  },
  plugins: []
};
