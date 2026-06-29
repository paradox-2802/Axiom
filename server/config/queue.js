import { Queue } from "bullmq";

export const uploadQueue = new Queue("file-upload-queue", {
    connection: {
        host: process.env.REDIS_HOST || "localhost",
        port: Number(process.env.REDIS_PORT || 6379),
    },
});
