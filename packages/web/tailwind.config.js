/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        birdlife: {
          bg: "#f8fafb",
          card: "#ffffff",
          border: "#d0dae0",
          text: "#1a2a3a",
          muted: "#6b7b8a",
          primary: "#2d7a8c",
          "primary-hover": "#1d5a6c",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
