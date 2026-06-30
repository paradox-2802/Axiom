import { LogOut, Moon, Sun } from "lucide-react";
import { motion } from "framer-motion";
import { logout } from "../../utils/auth";
import Logo from "../Logo";

export default function TopNav({ userName, theme, onToggleTheme }) {
  const isDark = theme === "dark";

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="h-14 surface-panel flex items-center px-4 sm:px-6 flex-shrink-0 z-30 backdrop-blur-md bg-white/90 dark:bg-slate-900/90"
    >
      <Logo size="sm" />

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <button
          type="button"
          onClick={onToggleTheme}
          className="btn-ghost !p-2"
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
        <span className="type-caption hidden sm:inline truncate max-w-[160px] px-2">
          {userName}
        </span>
        <button type="button" onClick={logout} className="btn-ghost">
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </motion.header>
  );
}
