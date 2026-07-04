/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c2027",
        muted: "#6b7280",
        panel: "#ffffff",
        line: "#d9dee7",
        paper: "#f5f7fa",
        teal: "#1f9d8a",
        coral: "#df5b45",
        amber: "#c88719",
        violet: "#7257d5"
      },
      boxShadow: {
        panel: "0 10px 30px rgba(28, 32, 39, 0.08)"
      }
    }
  },
  plugins: []
};
