import { motion, AnimatePresence } from "framer-motion";
import { Leaf, PanelLeftClose, Plus, MessageSquare, Trash2, User, LogOut } from "lucide-react";

export default function Sidebar({
    sidebarOpen,
    setSidebarOpen,
    darkMode,
    createNewChat,
    chatHistory,
    currentChatId,
    setCurrentChatId,
    deleteChat,
    userName,
    logout
}) {
    return (
        <>
            <AnimatePresence mode="wait">
                {sidebarOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setSidebarOpen(false)}
                        className="fixed inset-0 bg-black/60 z-40 lg:hidden"
                    />
                )}
            </AnimatePresence>

            <AnimatePresence mode="popLayout">
                {sidebarOpen && (
                    <motion.aside
                        initial={{ x: -320, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: -320, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className={`fixed inset-y-0 left-0 z-40 w-80 
              ${darkMode ? "bg-gray-900 border-r border-gray-800" : "bg-white border-r border-gray-200"} 
              shadow-2xl flex flex-col h-full`}
                    >
                        <div className="p-6">
                            <div className="flex items-center gap-4 mb-8">
                                <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center shadow-lg shadow-green-500/30 text-white">
                                    <Leaf className="w-7 h-7" />
                                </div>
                                <div>
                                    <h1 className={`font-bold text-2xl tracking-tight ${darkMode ? "text-green-500" : "text-green-600"}`}>AgroSathi</h1>
                                    <p className={`text-xs font-medium ${darkMode ? "text-gray-400" : "text-gray-500"}`}>Agriculture Assistant</p>
                                </div>
                                <button
                                    onClick={() => setSidebarOpen(false)}
                                    className="ml-auto p-2 rounded-xl active:scale-95 transition"
                                >
                                    <PanelLeftClose className="w-5 h-5" />
                                </button>
                            </div>

                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={createNewChat}
                                className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-4 rounded-xl flex gap-2 items-center justify-center shadow-lg shadow-green-600/25 font-semibold text-sm group transition-all"
                            >
                                <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform" /> New Chat
                            </motion.button>
                        </div>

                        <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 custom-scrollbar">
                            <div className="space-y-2">
                                <p className={`text-xs font-semibold uppercase tracking-wider mb-4 px-2 ${darkMode ? "text-gray-500" : "text-gray-400"}`}>History</p>
                                {chatHistory.map((c) => (
                                    <motion.div
                                        key={c.id}
                                        layout
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        onClick={() => {
                                            setCurrentChatId(c.id);
                                            if (window.innerWidth < 1024) setSidebarOpen(false);
                                        }}
                                        className={`group flex justify-between items-center gap-2 px-4 py-3.5 rounded-xl cursor-pointer transition-all ${c.id === currentChatId
                                            ? darkMode
                                                ? "bg-gray-800 shadow-lg shadow-black/10 border border-gray-700 text-white"
                                                : "bg-white shadow-lg shadow-green-100/50 border border-green-100 text-green-700"
                                            : darkMode
                                                ? "hover:bg-gray-800 text-gray-400 hover:text-gray-200"
                                                : "hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                                            }`}
                                    >
                                        <div className="flex gap-3 items-center truncate flex-1 min-w-0">
                                            <MessageSquare
                                                className={`w-4 h-4 flex-shrink-0 ${c.id === currentChatId
                                                    ? "text-green-500"
                                                    : "opacity-50"
                                                    }`}
                                            />
                                            <span className="truncate text-sm font-medium">
                                                {c.title}
                                            </span>
                                        </div>
                                        {c.id === currentChatId && (
                                            <motion.button
                                                initial={{ opacity: 0, scale: 0.5 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                onClick={(e) => deleteChat(c.id, e)}
                                                className="flex-shrink-0 p-1.5 hover:bg-red-50 rounded-lg group/del transition-colors"
                                                title="Delete chat"
                                            >
                                                <Trash2 className="w-4 h-4 text-red-400 group-hover/del:text-red-500" />
                                            </motion.button>
                                        )}
                                    </motion.div>
                                ))}
                            </div>
                        </div>

                        <div className="p-4 border-t border-gray-100/10">
                            <div className={`p-4 rounded-2xl ${darkMode ? "bg-gray-800" : "bg-gray-50"} flex items-center gap-3 shadow-sm border ${darkMode ? "border-gray-700" : "border-gray-200"}`}>
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center text-white font-bold shadow-md">
                                    <User className="w-5 h-5" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className={`text-sm font-bold truncate ${darkMode ? "text-gray-200" : "text-gray-800"}`}>{userName}</p>
                                </div>
                                <button
                                    onClick={logout}
                                    className="p-2 hover:bg-black/5 rounded-lg transition-colors text-gray-500 hover:text-red-500"
                                >
                                    <LogOut className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>
        </>
    );
}
