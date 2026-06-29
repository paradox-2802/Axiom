/**
 * AI Service
 * Provides question rewriting for improved RAG retrieval
 */

import { hfClient } from "../config/ai.js";

/**
 * Rewrites follow-up questions into standalone agricultural queries
 * Uses LLM to extract crop and topic context from conversation history
 * @param {string} question - User's follow-up question
 * @param {string} history - Recent conversation history for context
 * @returns {Promise<string>} Rewritten standalone question
 */
export async function rewriteQuestion(question, history) {
    const prompt = `
You rewrite follow-up questions into standalone agriculture questions.

Conversation:
${history}

Follow-up question:
${question}

Rewrite it as a complete standalone question.
- Mention crop explicitly
- Mention topic (fertilizer, pest, irrigation, etc)
- Do NOT answer
`;

    const res = await hfClient.chatCompletion({
        model: "meta-llama/Meta-Llama-3.1-8B-Instruct",
        messages: [{ role: "user", content: prompt }],
        temperature: 0,
        max_tokens: 80,
    });

    return res.choices[0].message.content.trim();
}
