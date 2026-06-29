/**
 * RSS Service - Background Worker
 * Fetches agricultural news and government schemes every 12 hours
 * Extracts content summaries and stores in MongoDB for the Notices feature
 */

import dotenv from "dotenv";
dotenv.config();

import cron from "node-cron";
import connectDB from "./config/db.js";
import { processFeeds } from "./jobs/rssExecutor.js";

console.log("🚀 AgroSathi RSS Service Starting...");

// Connect to MongoDB
await connectDB();

/**
 * Main execution function
 * Processes all whitelisted RSS feeds
 */
async function run() {
    try {
        await processFeeds();
    } catch (error) {
        console.error("❌ Critical Error in RSS Loop:", error);
    }
}

// Run immediately on startup
run();

// Schedule periodic execution using node-cron (every 12 hours at minute 0)
// Cron expression: '0 */12 * * *' = At minute 0 past every 12th hour
const scheduledTask = cron.schedule("0 */12 * * *", () => {
    console.log("⏰ Cron triggered - Running RSS feed processing...");
    run();
});

console.log("✅ Cron scheduler active. Running every 12 hours.");

/**
 * Graceful shutdown handler
 * Stops cron job and closes MongoDB connection
 */
async function gracefulShutdown(signal) {
    console.log(`\n🛑 ${signal} received. Shutting down gracefully...`);

    // Stop the cron scheduler
    scheduledTask.stop();
    console.log("⏹️  Cron scheduler stopped.");

    // Close MongoDB connection
    const mongoose = (await import("mongoose")).default;
    await mongoose.connection.close();
    console.log("🔌 MongoDB connection closed.");

    console.log("👋 RSS Service shutdown complete.");
    process.exit(0);
}

// Handle termination signals
process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT", () => gracefulShutdown("SIGINT"));
