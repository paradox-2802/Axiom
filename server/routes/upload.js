import express from "express";
import { uploadPDF } from "../controllers/uploadController.js";
import { adminMiddleware } from "../middleware/auth.js";
import { pdfUpload } from "../utils/multer.js";

const router = express.Router();

router.post("/pdf", adminMiddleware, pdfUpload.single("pdf"), uploadPDF);

export default router;
