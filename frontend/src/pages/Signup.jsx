import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { setAuth } from "../utils/auth";
import { API_BASE } from "../utils/api";
import ThemeToggle from "../components/ThemeToggle";
import Logo from "../components/Logo";
import { Title, Label, Caption } from "../components/Typography";

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e?.preventDefault();
    if (!form.name || !form.email || !form.password || loading) return;

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      let data = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }

      if (!res.ok) {
        setError(data?.error || "Signup failed");
        return;
      }

      setAuth(data);
      navigate("/");
    } catch {
      setError("Server error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-slate-950 mesh-bg px-4 relative">
      <ThemeToggle className="absolute top-4 right-4" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        className="w-full max-w-md surface-panel p-8 rounded-2xl shadow-card dark:shadow-card-dark"
      >
        <div className="flex justify-center mb-8">
          <Logo size="lg" />
        </div>

        <Title as="h2" className="mb-6 text-center text-slate-700 dark:text-slate-300">
          Create your account
        </Title>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label className="block mb-1.5">Full name</Label>
            <input
              type="text"
              placeholder="Your name"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 px-3.5 py-2.5 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              value={form.name}
              onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
              required
            />
          </div>

          <div>
            <Label className="block mb-1.5">Email</Label>
            <input
              type="email"
              placeholder="you@company.com"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 px-3.5 py-2.5 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              required
            />
          </div>

          <div>
            <Label className="block mb-1.5">Password</Label>
            <input
              type="password"
              placeholder="Minimum 6 characters"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 px-3.5 py-2.5 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              value={form.password}
              onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
              required
              minLength={6}
            />
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full !py-3">
            {loading ? (
              <>
                <Loader2 className="animate-spin w-5 h-5" />
                Creating account...
              </>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        <Caption className="text-center mt-6">
          Already have an account?{" "}
          <a href="/login" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Sign in
          </a>
        </Caption>
      </motion.div>
    </div>
  );
}
