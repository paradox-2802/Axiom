import { useState, useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ArrowUp, FileBarChart, Shield, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  authFetch,
  fetchExecutiveSummary,
  fetchRiskAnalysis,
  generateExecutiveSummary,
  generateRiskAnalysis,
} from "../utils/api";
import { consumeChatStream } from "../utils/streamChat";
import { getUser } from "../utils/auth";
import { getStoredTheme, toggleTheme } from "../utils/theme";
import { formatRisksMarkdown, formatSummaryMarkdown } from "../utils/formatInsights";
import { stripThinkingBlocks } from "../utils/stripThinking";

function sanitizeMessages(messages = []) {
  return messages.map((m) =>
    m.role === "assistant" && m.content
      ? { ...m, content: stripThinkingBlocks(m.content) }
      : m
  );
}

import TopNav from "../components/chat/TopNav";
import IconSidebar from "../components/chat/IconSidebar";
import WorkspacePanel from "../components/chat/WorkspacePanel";
import DocumentUpload from "../components/chat/DocumentUpload";
import CitationList from "../components/chat/CitationList";
import { LogoMark } from "../components/Logo";
import { HeroReveal } from "../components/effects/RevealText";
import { heroCtaDelay } from "../components/effects/heroTiming";

function getSessionState(meta, messageCount) {
  if (!meta) return "needsUpload";
  const { documentUploaded, ingestionStatus } = meta;
  if (documentUploaded) {
    if (ingestionStatus === "processing") return "processing";
    if (ingestionStatus === "failed") return "failed";
    if (ingestionStatus === "completed") return "ready";
    return "processing";
  }
  if (messageCount > 0) return "ready";
  return "needsUpload";
}

const WELCOME_MESSAGE =
  "Your document is ready. Ask me anything about this financial report.";

const INSIGHT_PROMPTS = {
  summary: "Generate Executive Summary",
  risks: "Extract Risks",
};

const markdownComponents = {
  p: (props) => <p {...props} />,
  ul: (props) => <ul className="list-disc pl-4" {...props} />,
  ol: (props) => <ol className="list-decimal pl-4" {...props} />,
  li: (props) => <li {...props} />,
  strong: (props) => <strong className="font-semibold" {...props} />,
  h3: (props) => <h3 {...props} />,
};

export default function Chatbot() {
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [chats, setChats] = useState({});
  const [sessionMeta, setSessionMeta] = useState({});
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [generatingInsight, setGeneratingInsight] = useState(null);
  const [workspacesOpen, setWorkspacesOpen] = useState(false);
  const [showSources, setShowSources] = useState({});
  const [userName, setUserName] = useState("User");
  const [theme, setTheme] = useState(getStoredTheme);
  const reduceMotion = useReducedMotion();

  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const shouldAutoScrollRef = useRef(true);
  const streamContentRef = useRef("");

  const scrollToBottom = () => {
    if (!shouldAutoScrollRef.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    shouldAutoScrollRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };

  const updateLastAssistantMessage = (chatId, updater) => {
    setChats((prev) => {
      const messages = [...(prev[chatId] || [])];
      let lastIndex = messages.length - 1;
      if (lastIndex < 0 || messages[lastIndex].role !== "assistant") {
        messages.push({
          role: "assistant",
          content: streamContentRef.current,
          sources: [],
          isStreaming: true,
        });
        lastIndex = messages.length - 1;
      }
      messages[lastIndex] = updater(messages[lastIndex]);
      return { ...prev, [chatId]: messages };
    });
  };

  const setLastAssistantContent = (chatId, content) => {
    setChats((prev) => {
      const messages = [...(prev[chatId] || [])];
      const lastIndex = messages.length - 1;
      if (lastIndex >= 0 && messages[lastIndex].role === "assistant") {
        messages[lastIndex] = {
          ...messages[lastIndex],
          content,
          isStreaming: false,
        };
      }
      return { ...prev, [chatId]: messages };
    });
  };

  useEffect(() => {
    const user = getUser();
    if (user?.name) setUserName(user.name);
  }, []);

  const handleToggleTheme = () => {
    setTheme(toggleTheme());
  };

  useEffect(() => {
    authFetch("/chat/list")
      .then((r) => r.json())
      .then((data) => {
        setChatHistory(
          data.map((c) => ({
            id: c.id,
            title: c.title || "New Chat",
            updatedAt: c.updatedAt,
            ingestionStatus: c.ingestionStatus || "pending",
          }))
        );
        setSessionMeta((prev) => {
          const next = { ...prev };
          data.forEach((c) => {
            next[c.id] = {
              documentName: c.documentName,
              documentUploaded: c.documentUploaded,
              ingestionStatus: c.ingestionStatus || "pending",
            };
          });
          return next;
        });
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!currentChatId) return;

    authFetch(`/chat/history/${currentChatId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setSessionMeta((p) => ({
          ...p,
          [currentChatId]: {
            documentName: d.documentName,
            documentUploaded: d.documentUploaded,
            documentLocked: d.documentLocked,
            ingestionStatus: d.ingestionStatus || "pending",
          },
        }));
        const messageCount = d.messages?.length || 0;
        const state = getSessionState(
          { documentUploaded: d.documentUploaded, ingestionStatus: d.ingestionStatus },
          messageCount
        );
        setChats((p) => ({
          ...p,
          [currentChatId]:
            messageCount > 0
              ? sanitizeMessages(d.messages)
              : state === "ready"
                ? [{ role: "assistant", content: WELCOME_MESSAGE }]
                : [],
        }));
      })
      .catch(() => {});
  }, [currentChatId]);

  useEffect(() => {
    const meta = sessionMeta[currentChatId];
    if (!currentChatId || meta?.ingestionStatus !== "processing") return;

    const interval = setInterval(() => {
      authFetch(`/chat/history/${currentChatId}`)
        .then((r) => r.json())
        .then((d) => {
          if (!d) return;
          setSessionMeta((p) => ({
            ...p,
            [currentChatId]: {
              documentName: d.documentName,
              documentUploaded: d.documentUploaded,
              documentLocked: d.documentLocked,
              ingestionStatus: d.ingestionStatus || "pending",
            },
          }));
          if (d.ingestionStatus === "completed") {
            const title =
              d.documentName?.replace(/\.pdf$/i, "") || d.title || "New Chat";
            setChatHistory((p) =>
              p.map((c) =>
                c.id === currentChatId
                  ? { ...c, title, ingestionStatus: "completed" }
                  : c
              )
            );
            setChats((p) => ({
              ...p,
              [currentChatId]: p[currentChatId]?.length
                ? p[currentChatId]
                : [{ role: "assistant", content: WELCOME_MESSAGE }],
            }));
          }
        })
        .catch(() => {});
    }, 2000);

    return () => clearInterval(interval);
  }, [currentChatId, sessionMeta]);

  useEffect(() => {
    scrollToBottom();
  }, [chats, currentChatId, isLoading, generatingInsight]);

  const createNewChat = async () => {
    const id = Date.now().toString();
    try {
      await authFetch("/chat/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chatId: id }),
      });
      setChatHistory((p) => [{ id, title: "New workspace", ingestionStatus: "pending" }, ...p]);
      setChats((p) => ({ ...p, [id]: [] }));
      setSessionMeta((p) => ({
        ...p,
        [id]: { documentName: null, documentUploaded: false, ingestionStatus: "pending" },
      }));
      setCurrentChatId(id);
    } catch {
      alert("Failed to create workspace.");
    }
  };

  const deleteChat = async (id, e) => {
    e.stopPropagation();
    if (!confirm("Delete this workspace?")) return;
    try {
      const response = await authFetch(`/chat/${id}`, { method: "DELETE" });
      const result = await response.json();
      if (!result.success) return;
      setChatHistory((p) => p.filter((c) => c.id !== id));
      setChats((p) => {
        const c = { ...p };
        delete c[id];
        return c;
      });
      if (id === currentChatId) setCurrentChatId(null);
      setSessionMeta((p) => {
        const next = { ...p };
        delete next[id];
        return next;
      });
    } catch {
      alert("Failed to delete workspace.");
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isLoading || generatingInsight || !currentChatId) return;
    const chatId = currentChatId;
    const msg = input.trim();
    const messageCount = (chats[chatId] || []).length;
    const state = getSessionState(sessionMeta[chatId], messageCount);
    if (state !== "ready") return;

    setInput("");
    streamContentRef.current = "";

    flushSync(() => {
      setChats((p) => ({
        ...p,
        [chatId]: [
          ...(p[chatId] || []),
          { role: "user", content: msg },
          { role: "assistant", content: "", sources: [], isStreaming: true },
        ],
      }));
    });

    setIsLoading(true);
    shouldAutoScrollRef.current = true;

    try {
      const res = await authFetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chatId, message: msg }),
      });
      if (!res.ok) throw new Error("Failed");

      let sources = [];
      let title = "";

      await consumeChatStream(res, (data) => {
        if (data.error) {
          streamContentRef.current = data.error;
          updateLastAssistantMessage(chatId, (m) => ({
            ...m,
            content: data.error,
            isStreaming: false,
          }));
        }
        if (data.content) {
          streamContentRef.current += data.content;
          updateLastAssistantMessage(chatId, (m) => ({
            ...m,
            content: stripThinkingBlocks(streamContentRef.current),
          }));
        }
        if (data.sources) sources = data.sources;
        if (data.title) title = data.title;
        if (data.done) {
          const cleaned = stripThinkingBlocks(streamContentRef.current || "");
          streamContentRef.current = cleaned;
          updateLastAssistantMessage(chatId, (m) => ({
            ...m,
            content: cleaned || m.content,
            sources,
            isStreaming: false,
          }));
          if (title) {
            setChatHistory((p) =>
              p.map((c) => (c.id === chatId ? { ...c, title } : c))
            );
          }
        }
      });
    } catch {
      setChats((p) => {
        const messages = [...(p[chatId] || [])];
        messages[messages.length - 1] = {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          isStreaming: false,
        };
        return { ...p, [chatId]: messages };
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleInsightRequest = async (type) => {
    if (!currentChatId || isLoading || generatingInsight) return;
    const chatId = currentChatId;
    const messageCount = (chats[chatId] || []).length;
    const state = getSessionState(sessionMeta[chatId], messageCount);
    if (state !== "ready") return;

    const userQuestion = INSIGHT_PROMPTS[type];

    flushSync(() => {
      setChats((p) => ({
        ...p,
        [chatId]: [
          ...(p[chatId] || []),
          { role: "user", content: userQuestion },
          { role: "assistant", content: "", isStreaming: true },
        ],
      }));
    });

    setGeneratingInsight(type);
    shouldAutoScrollRef.current = true;

    try {
      const fetchFn = type === "summary" ? fetchExecutiveSummary : fetchRiskAnalysis;
      const generateFn = type === "summary" ? generateExecutiveSummary : generateRiskAnalysis;
      const formatFn = type === "summary" ? formatSummaryMarkdown : formatRisksMarkdown;

      let result = await fetchFn(chatId);
      if (result.status === "idle" || result.status === "failed") {
        result = await generateFn(chatId);
      }

      let content;
      if (result.status === "ready" && result.data) {
        content = formatFn(result.data);
      } else if (result.status === "generating") {
        result = await generateFn(chatId);
        content =
          result.status === "ready" && result.data
            ? formatFn(result.data)
            : result.error || "Generation is taking longer than expected. Please try again.";
      } else {
        content = result.error || "Something went wrong. Please try again.";
      }

      setLastAssistantContent(chatId, content);
    } catch {
      setLastAssistantContent(
        chatId,
        "Failed to generate a response. Please try again."
      );
    } finally {
      setGeneratingInsight(null);
    }
  };

  const handleUploadStarted = (data) => {
    setSessionMeta((p) => ({
      ...p,
      [currentChatId]: {
        documentName: data.documentName,
        documentUploaded: true,
        documentLocked: true,
        ingestionStatus: data.ingestionStatus || "processing",
      },
    }));
    const title = data.documentName?.replace(/\.pdf$/i, "") || "New workspace";
    setChatHistory((p) =>
      p.map((c) => (c.id === currentChatId ? { ...c, title, ingestionStatus: "processing" } : c))
    );
  };

  const currentMessages = chats[currentChatId] || [];
  const currentMeta = currentChatId ? sessionMeta[currentChatId] : null;
  const sessionState = getSessionState(currentMeta, currentMessages.length);
  const chatEnabled = sessionState === "ready";
  const showHero = !currentChatId || (chatEnabled && currentMessages.length <= 1);
  const inputBusy = isLoading || !!generatingInsight;

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden mesh-bg">
      <TopNav userName={userName} theme={theme} onToggleTheme={handleToggleTheme} />

      <div className="flex flex-1 min-h-0 relative">
        <IconSidebar
          onNewChat={createNewChat}
          onToggleWorkspaces={() => setWorkspacesOpen((v) => !v)}
          workspacesOpen={workspacesOpen}
        />

        <WorkspacePanel
          open={workspacesOpen}
          onClose={() => setWorkspacesOpen(false)}
          chatHistory={chatHistory}
          currentChatId={currentChatId}
          setCurrentChatId={setCurrentChatId}
          deleteChat={deleteChat}
          createNewChat={createNewChat}
        />

        <main className="flex-1 flex flex-col min-w-0 relative">
          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto custom-scrollbar relative z-10"
          >
            <div className="max-w-3xl mx-auto px-4 py-8 w-full">
              {showHero && (
                <div className="flex flex-col items-center gap-5 mb-8 pt-6 sm:pt-10">
                  <motion.div
                    initial={{ opacity: 0, scale: 0.94 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className="inline-flex"
                  >
                    <LogoMark size="lg" />
                  </motion.div>
                  <HeroReveal />
                </div>
              )}

              {!currentChatId && (
                <motion.div
                  initial={{ opacity: 0, y: 8, filter: "blur(4px)" }}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{
                    delay: showHero ? heroCtaDelay(reduceMotion) : 0.15,
                    duration: 0.4,
                    ease: "easeOut",
                  }}
                  className="text-center mt-1"
                >
                  <button type="button" onClick={createNewChat} className="btn-primary">
                    Create workspace
                  </button>
                </motion.div>
              )}

              {currentChatId && !chatEnabled && (
                <DocumentUpload
                  chatId={currentChatId}
                  sessionState={sessionState}
                  documentName={currentMeta?.documentName}
                  onUploadStarted={handleUploadStarted}
                />
              )}

              {currentChatId && chatEnabled && currentMeta?.documentName && (
                <DocumentUpload
                  chatId={currentChatId}
                  sessionState="ready"
                  documentName={currentMeta.documentName}
                  onUploadStarted={handleUploadStarted}
                />
              )}

              <AnimatePresence initial={false}>
              {currentChatId &&
                currentMessages.map((m, i) => {
                  const isStreaming =
                    m.role === "assistant" && m.isStreaming && i === currentMessages.length - 1;
                  const showDots = isStreaming && !stripThinkingBlocks(m.content);
                  const assistantText = stripThinkingBlocks(m.content);

                  return (
                    <motion.div
                      key={`${currentChatId}-${i}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.28, ease: "easeOut" }}
                      className={`flex gap-3 mb-6 ${m.role === "user" ? "justify-end" : ""}`}
                    >
                      {m.role === "assistant" && (
                        <LogoMark size="xs" className="flex-shrink-0 mt-0.5" />
                      )}
                      <div className={`max-w-[85%] ${m.role === "user" ? "order-first" : ""}`}>
                        <div
                          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed transition-shadow duration-200 ${
                            m.role === "user"
                              ? "bg-brand-600 text-white rounded-tr-md shadow-sm"
                              : "surface-panel rounded-tl-md shadow-sm"
                          }`}
                        >
                          {showDots ? (
                            <div className="flex gap-1.5 py-1">
                              {[0, 150, 300].map((delay) => (
                                <div
                                  key={delay}
                                  className="w-2 h-2 bg-brand-400 rounded-full animate-bounce"
                                  style={{ animationDelay: `${delay}ms` }}
                                />
                              ))}
                            </div>
                          ) : m.role === "user" ? (
                            m.content
                          ) : isStreaming ? (
                            <div className="chat-markdown whitespace-pre-wrap text-slate-800 dark:text-slate-100">
                              {assistantText}
                              <span className="inline-block w-1.5 h-4 ml-0.5 bg-brand-500 animate-pulse align-middle rounded-sm" />
                            </div>
                          ) : (
                            <div className="chat-markdown text-slate-800 dark:text-slate-100">
                              <ReactMarkdown components={markdownComponents}>
                                {assistantText}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                        {m.role === "assistant" && m.sources?.length > 0 && !isStreaming && (
                          <CitationList
                            sources={m.sources}
                            expanded={!!showSources[i]}
                            onToggle={() =>
                              setShowSources((p) => ({ ...p, [i]: !p[i] }))
                            }
                          />
                        )}
                      </div>
                      {m.role === "user" && (
                        <div className="w-8 h-8 rounded-xl bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
                          <User className="w-4 h-4 text-slate-600 dark:text-slate-300" />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              <div ref={messagesEndRef} />
            </div>
          </div>

          {currentChatId && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="px-4 py-4 flex-shrink-0 relative z-10"
            >
              <div className="max-w-3xl mx-auto w-full">
                <div className="input-surface">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmit();
                      }
                    }}
                    rows={2}
                    placeholder={
                      !chatEnabled
                        ? "Upload a PDF to start chatting…"
                        : "Ask about revenue, risks, outlook, or any figure in your document…"
                    }
                    disabled={!chatEnabled || inputBusy}
                    className="w-full resize-none bg-transparent px-4 pt-4 pb-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none disabled:opacity-50"
                  />
                  <div className="flex items-center justify-between gap-2 px-3 pb-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {chatEnabled && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleInsightRequest("summary")}
                            disabled={inputBusy}
                            className="btn-chip"
                          >
                            <FileBarChart className="w-3.5 h-3.5" />
                            Summary
                          </button>
                          <button
                            type="button"
                            onClick={() => handleInsightRequest("risks")}
                            disabled={inputBusy}
                            className="btn-chip"
                          >
                            <Shield className="w-3.5 h-3.5" />
                            Risks
                          </button>
                        </>
                      )}
                    </div>
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={handleSubmit}
                      disabled={!input.trim() || inputBusy || !chatEnabled}
                      className="w-9 h-9 rounded-full bg-brand-600 hover:bg-brand-700 disabled:bg-slate-200 dark:disabled:bg-slate-700 disabled:cursor-not-allowed text-white flex items-center justify-center transition-colors flex-shrink-0 shadow-sm"
                    >
                      {isLoading ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <ArrowUp className="w-4 h-4" />
                      )}
                    </motion.button>
                  </div>
                </div>

                <p className="type-caption text-center mt-3">
                  Answers are grounded in your uploaded document. Verify important figures.
                </p>
              </div>
            </motion.div>
          )}
        </main>
      </div>
    </div>
  );
}
