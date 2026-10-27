import os
import subprocess
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Media Transcoder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscodeRequest(BaseModel):
    url: str
    format: str  # 'mkv' or 'aa3'

@app.get("/")
def health_check():
    return {"status": "online", "message": "Media Transcoder API is running"}

@app.post("/api/transcode")
def process_media(req: TranscodeRequest):
    job_id = str(uuid.uuid4())
    work_dir = f"/tmp/{job_id}"
    os.makedirs(work_dir, exist_ok=True)

    if req.format == "mkv":
        out_file = os.path.join(work_dir, "output.mkv")
        cmd = [
            "yt-dlp",
            "-f", "bv*+ba/b",
            "--merge-output-format", "mkv",
            "-o", out_file,
            req.url
        ]
        try:
            subprocess.run(cmd, check=True)
            return FileResponse(out_file, media_type="video/x-matroska", filename="video.mkv")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail="Failed to fetch and transcode video to MKV.")

    elif req.format == "aa3":
        raw_wav = os.path.join(work_dir, "raw.wav")
        out_file = os.path.join(work_dir, "output.aa3")
        try:
            # 1. Extract audio to standard PCM WAV
            subprocess.run([
                "yt-dlp",
                "-x",
                "--audio-format", "wav",
                "-o", raw_wav,
                req.url
            ], check=True)

            # 2. Transcode PCM WAV into Sony ATRAC3 (.aa3)
            subprocess.run([
                "ffmpeg",
                "-y",
                "-i", raw_wav,
                "-c:a", "atrac3",
                "-b:a", "132k",
                out_file
            ], check=True)

            return FileResponse(out_file, media_type="audio/x-oma", filename="audio.aa3")
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail="Failed to transcode audio to Sony AA3 format.")

    else:
        raise HTTPException(status_code=400, detail="Invalid format requested.")
