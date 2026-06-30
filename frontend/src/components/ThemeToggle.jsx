import { useState } from "react";
import { Moon, Sun } from "lucide-react";
import { getStoredTheme, toggleTheme } from "../utils/theme";

export default function ThemeToggle({ className = "" }) {
  const [theme, setTheme] = useState(getStoredTheme);

  const handleToggle = () => {
    setTheme(toggleTheme());
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      className={`btn-ghost !p-2 ${className}`}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
}
