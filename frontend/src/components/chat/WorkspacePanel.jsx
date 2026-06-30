import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Trash2, X } from "lucide-react";

function formatUpdatedAt(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function statusLabel(status) {
  if (status === "completed") return "Ready";
  if (status === "processing") return "Processing";
  if (status === "failed") return "Failed";
  return "Upload PDF";
}

export default function WorkspacePanel({
  open,
  onClose,
  chatHistory,
  currentChatId,
  setCurrentChatId,
  deleteChat,
  createNewChat,
}) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-slate-900/20 dark:bg-black/40 z-30 lg:hidden backdrop-blur-[2px]"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: -16, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -16, opacity: 0 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
            className="absolute left-14 top-0 bottom-0 w-72 surface-panel z-30 flex flex-col shadow-card dark:shadow-card-dark"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
              <h2 className="type-section text-base">
                Workspaces
              </h2>
              <button type="button" onClick={onClose} className="btn-ghost !p-1.5">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3">
              <button
                type="button"
                onClick={() => {
                  createNewChat();
                  onClose();
                }}
                className="btn-primary w-full !rounded-xl"
              >
                + New workspace
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pb-4 custom-scrollbar">
              {chatHistory.length === 0 && (
                <p className="type-caption px-2 py-4">No workspaces yet.</p>
              )}
              {chatHistory.map((c, i) => (
                <motion.button
                  key={c.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  type="button"
                  onClick={() => {
                    setCurrentChatId(c.id);
                    onClose();
                  }}
                  className={`w-full text-left flex items-start gap-3 px-3 py-3 rounded-xl mb-1 transition-all duration-200 group ${
                    c.id === currentChatId
                      ? "bg-brand-50 dark:bg-brand-500/10 border border-brand-200/80 dark:border-brand-500/25 shadow-sm"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/80 border border-transparent"
                  }`}
                >
                  <MessageSquare
                    className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                      c.id === currentChatId
                        ? "text-brand-600 dark:text-brand-400"
                        : "text-slate-400"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                      {c.title}
                    </p>
                    <p className="type-caption mt-0.5">
                      {statusLabel(c.ingestionStatus)}
                      {c.updatedAt ? ` · ${formatUpdatedAt(c.updatedAt)}` : ""}
                    </p>
                  </div>
                  {c.id === currentChatId && (
                    <button
                      type="button"
                      onClick={(e) => deleteChat(c.id, e)}
                      className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-500/10 text-red-400 hover:text-red-500 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </motion.button>
              ))}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
