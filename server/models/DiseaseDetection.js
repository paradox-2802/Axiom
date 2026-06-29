import mongoose from "mongoose";

const MessageSchema = new mongoose.Schema(
    {
        role: { type: String, enum: ["user", "assistant"], required: true },
        content: { type: String, required: true },
        hasImage: { type: Boolean, default: false },
        imagePath: { type: String }, // Path to stored image
        imageDescription: { type: String },
    },
    { timestamps: true }
);

const DiseaseDetectionSchema = new mongoose.Schema(
    {
        userId: { type: mongoose.Schema.Types.ObjectId, required: true },
        chatId: { type: String, required: true },
        title: { type: String, default: "New Diagnosis" },
        messages: { type: [MessageSchema], default: [] },
    },
    { timestamps: true }
);

DiseaseDetectionSchema.index({ userId: 1, chatId: 1 }, { unique: true });

export default mongoose.model("DiseaseDetection", DiseaseDetectionSchema);
