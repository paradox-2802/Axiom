import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { uploadDocument } from "../../utils/api";

export default function DocumentUpload({
  chatId,
  sessionState,
  documentName,
  onUploadStarted,
}) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = useCallback(
    async (file) => {
      if (!file || !chatId) return;
      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please upload a PDF file.");
        return;
      }

      setError("");
      setUploading(true);

      try {
        const res = await uploadDocument(chatId, file);
        const data = await res.json();

        if (res.status === 409) {
          setError(
            data.message ||
              "This session is already linked to a document. Create a new workspace to analyse another report."
          );
          return;
        }

        if (!res.ok) {
          throw new Error(data.error || data.message || "Upload failed");
        }

        onUploadStarted(data);
      } catch (err) {
        setError(err.message || "Failed to upload document. Please try again.");
      } finally {
        setUploading(false);
      }
    },
    [chatId, onUploadStarted]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  if (sessionState === "processing" || uploading) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center py-16 text-center"
      >
        <Loader2 className="w-11 h-11 text-brand-600 animate-spin mb-4" />
        <h3 className="type-section mb-2">
          Processing document
        </h3>
        <p className="type-caption max-w-sm">
          Indexing your financial report for analysis. This usually takes a moment.
        </p>
      </motion.div>
    );
  }

  if (sessionState === "failed") {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex flex-col items-center justify-center py-16 text-center max-w-md mx-auto"
      >
        <AlertCircle className="w-11 h-11 text-red-500 mb-4" />
        <h3 className="type-section mb-2">
          Processing failed
        </h3>
        <p className="type-caption">
          We could not index {documentName || "your document"}. Create a new workspace and try again.
        </p>
      </motion.div>
    );
  }

  if (sessionState === "ready" && documentName) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto max-w-lg rounded-2xl border p-4 mb-4 surface-panel shadow-card dark:shadow-card-dark"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400 flex-shrink-0" />
          </div>
          <div className="min-w-0 flex-1 text-left">
            <p className="type-overline">
              Active document
            </p>
            <p className="text-sm font-medium truncate text-slate-800 dark:text-slate-100">
              {documentName}
            </p>
          </div>
          <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 text-sm font-medium">
            <CheckCircle2 className="w-4 h-4" />
            Ready
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="flex flex-col items-center justify-center py-10 max-w-xl mx-auto w-full text-center px-4"
    >
      <h2 className="type-title mb-2">
        Upload financial report
      </h2>
      <p className="type-caption mb-8 max-w-sm">
        Each workspace analyses one PDF. Upload an annual report, 10-K, or earnings document to begin.
      </p>

      <motion.div
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer w-full rounded-2xl border-2 border-dashed p-10 transition-all duration-300 ${
          isDragging
            ? "border-brand-500 bg-brand-50/80 dark:bg-brand-500/10 shadow-glow"
            : "border-slate-200 dark:border-slate-700 hover:border-brand-400 dark:hover:border-brand-500/50 bg-white dark:bg-slate-800/40"
        }`}
      >
        <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-brand-50 dark:bg-brand-500/10 flex items-center justify-center">
          <Upload className="w-7 h-7 text-brand-600 dark:text-brand-400" />
        </div>
        <p className="type-body font-medium mb-1 text-slate-800 dark:text-slate-100">Drag &amp; drop your PDF</p>
        <p className="type-caption">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </motion.div>

      {error && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-4 text-sm text-red-500 font-medium"
        >
          {error}
        </motion.p>
      )}
    </motion.div>
  );
}
