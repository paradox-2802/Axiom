import { motion } from "framer-motion";
import { Clock, Plus } from "lucide-react";

const iconBtn =
  "w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 active:scale-95";

export default function IconSidebar({ onNewChat, onToggleWorkspaces, workspacesOpen }) {
  return (
    <motion.aside
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-14 surface-panel flex flex-col items-center py-4 flex-shrink-0 z-20"
    >
      <button
        type="button"
        onClick={onNewChat}
        className={`${iconBtn} text-slate-500 dark:text-slate-400 hover:bg-brand-50 dark:hover:bg-brand-500/10 hover:text-brand-600 dark:hover:text-brand-400 mb-2`}
        title="New workspace"
      >
        <Plus className="w-5 h-5" />
      </button>

      <button
        type="button"
        onClick={onToggleWorkspaces}
        className={`${iconBtn} mb-2 ${
          workspacesOpen
            ? "bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300 shadow-sm"
            : "text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-slate-200"
        }`}
        title="Workspaces"
      >
        <Clock className="w-5 h-5" />
      </button>
    </motion.aside>
  );
}
