import express from "express";
import {
    createChat,
    deleteChat,
    listChats,
    getChatHistory,
    handleChat
} from "../controllers/chatController.js";
import { handleDiseaseDetection } from "../controllers/diseaseController.js";
import { authMiddleware } from "../middleware/auth.js";
import { imageUpload } from "../utils/multer.js";
import diseaseRoutes from "./disease.js";

const router = express.Router();

router.use("/disease", diseaseRoutes);

router.post("/create", authMiddleware, createChat);
router.delete("/:chatId", authMiddleware, deleteChat);
router.get("/list", authMiddleware, listChats);
router.get("/history/:chatId", authMiddleware, getChatHistory);
router.post("/", authMiddleware, handleChat);
router.post("/disease-detect", authMiddleware, imageUpload.single("image"), handleDiseaseDetection);

export default router;
