from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_groq import ChatGroq
import subprocess
import os
import requests
import json
import time

app = FastAPI()

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True, # Replace "*" with specific domains in production
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/process_voice")

async def process_voice(file: UploadFile = File(...)):
    file_path = os.path.abspath(f"./{file.filename}")  # Use absolute path for better file handling

    try:
        # Save the uploaded file to the local directory
        with open(file_path, "wb") as audio_file:
            audio_file.write(await file.read())
            print("File Path : " + file_path)

       
        transcription= transcribe_and_translate_audio(file_path)

        if transcription is None:
            raise ValueError("Transcription failed.")

        print("transcription: " + transcription)

        if not transcription:
            raise ValueError("Transcription failed.")
   
              
        summary =""
        summary  = summarize_with_ollama(transcription)
        print("summary: Groq : " + summary)
      

        if not summary:
            raise ValueError("Summary generation failed.")

        # Cleanup: Remove the saved file after processing
        os.remove(file_path)
        output =  {
        'transcription': transcription,
        'summary': summary
        }
        
        print(output)
        return output
 
    except Exception as e:
        print(f"Error in processing voice: {e}")  # Debug: Log the error
        return {"error": str(e)}


def transcribe_and_translate_audio(audio_file, target_language="en"):
    """
    Translates audio from any language to the specified target language using Whisper.
    """
    try:
        # Get absolute path and ensure file exists
        audio_file_path = os.path.abspath(audio_file)
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        # Define output directory and format
        output_dir = os.path.dirname(audio_file_path)
        output_format = "txt"

        # Run Whisper with translation task
        result = subprocess.run(
            [
                "whisper", audio_file_path, "--model", "base",
                "--task", "translate", "--language", target_language,
                "--output_dir", output_dir, "--output_format", output_format
            ],
            capture_output=True,
            text=True,
            shell=True  # Use shell=True for Windows
        )

        # Check for errors
        if result.returncode != 0:
            raise RuntimeError(f"Whisper failed: {result.stderr}")

        # Read translation from the generated file
        translation_file = os.path.join(
            output_dir, f"{os.path.basename(audio_file_path).split('.')[0]}.txt"
        )
        if os.path.exists(translation_file):
            with open(translation_file, "r", encoding="utf-8") as file:
                translation = file.read().strip()
            return translation
        else:
            raise FileNotFoundError(f"Translation file not found: {translation_file}")

    except Exception as e:
        print(f"Error during translation: {e}")
        return None

def summarize_with_ollama(text):
    """
    Sends text to the Ollama API for summarization.
    """
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3:latest",
        "prompt": text
    }
    headers = {"Content-Type": "application/json"}

    try:
        # Make the POST request with streaming enabled
        response = requests.post(url, json=payload, headers=headers, stream=True)
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")

        # Process the response line by line
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)  # Parse each line as JSON
                    full_response += chunk.get("response", "")  # Append "response" field
                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error: {e}, Line: {line}")

        if not full_response:
            raise Exception("No valid response from Ollama API.")

        return full_response

    except Exception as e:
        print(f"Error with Ollama API: {e}")
        return None


@app.get("/")
def root():
    return {"message": "Doctor-Patient Voice Processing Backend"}


# Example to verify Whisper and FFmpeg configurations
def verify_ffmpeg_installation():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("FFmpeg is installed and working correctly.")
        else:
            print("FFmpeg is not installed or not configured properly.")
            print(result.stderr)
    except FileNotFoundError:
        print("FFmpeg is not found. Please install it and ensure it's in your PATH.")

# Run this verification during startup
verify_ffmpeg_installation()
