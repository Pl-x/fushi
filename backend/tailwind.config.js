module.exports = {
  content: ['./src/app/templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        pink: {
          50: '#ecfdf5', 100: '#d1fae5', 300: '#6ee7b7',
          500: '#059669', 600: '#059669', 700: '#047857',
        },
        brand: { 700: '#047857' },
      },
    },
  },
  plugins: [],
};
