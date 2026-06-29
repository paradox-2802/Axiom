/**
 * Response Utility Functions
 * Provides shared helpers for standardized API responses and SSE (Server-Sent Events)
 */

/**
 * Sets standard headers for Server-Sent Events (SSE)
 * Used for streaming AI responses to the client
 * @param {Object} res - Express response object
 */
export const setSSEHeaders = (res) => {
    res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
};

/**
 * Sends a structured error response
 * Ensures headers haven't been sent before responding
 * @param {Object} res - Express response object
 * @param {number} status - HTTP status code
 * @param {string} message - Error message
 */
export const sendError = (res, status, message) => {
    if (!res.headersSent) {
        res.status(status).json({ error: message });
    } else {
        res.end();
    }
};
