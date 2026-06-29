import express from "express";
import {
    createDiseaseChat,
    listDiseaseChats,
    getDiseaseHistory,
    deleteDiseaseChat
} from "../controllers/diseaseController.js";
import { authMiddleware } from "../middleware/auth.js";

const router = express.Router();

router.post("/create", authMiddleware, createDiseaseChat);
router.get("/list", authMiddleware, listDiseaseChats);
router.get("/history/:chatId", authMiddleware, getDiseaseHistory);
router.delete("/:chatId", authMiddleware, deleteDiseaseChat);

export default router;
