import { ChevronDown, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

function formatSourceLabel(source) {
  const parts = [];
  if (source.page) parts.push(`Page ${source.page}`);
  if (source.sectionHeading) parts.push(source.sectionHeading);
  if (source.metadata?.documentTitle) parts.push(source.metadata.documentTitle);
  return parts.join(" · ") || "Document excerpt";
}

export default function CitationList({ sources = [], expanded, onToggle }) {
  if (!sources.length) return null;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={onToggle}
        className="btn-chip !py-1 !text-[11px] text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-500/10 border-brand-200/80 dark:border-brand-500/20"
      >
        <FileText className="w-3 h-3" />
        <span>
          {sources.length} source{sources.length !== 1 ? "s" : ""}
        </span>
        <ChevronDown
          className={`w-3 h-3 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden mt-2 space-y-2"
          >
            {sources.map((source, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="text-xs rounded-xl p-3 border surface-panel shadow-sm"
              >
                <p className="font-medium mb-1 text-brand-700 dark:text-brand-300">
                  {formatSourceLabel(source)}
                </p>
                <p className="leading-relaxed text-slate-600 dark:text-slate-300">
                  {source.preview}
                  {source.preview?.length >= 180 ? "…" : ""}
                </p>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
