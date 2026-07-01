/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#3b6cff",
          600: "#2956ed",
          700: "#1f44c2",
        },
      },
    },
  },
  plugins: [],
};
