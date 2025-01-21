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

        # Transcribe and translate the audio file
        transcription = transcribe_and_translate_audio_with_groq(file_path)

        # Check if transcription is None
        if transcription is None:
            raise ValueError("Transcription failed.")
        
        print("transcription: " + transcription)  # Only print if transcription is valid

        # Summarize the transcription using Groq or another model
        summary = summarize_groq_ollama(transcription)
        print("summary: Groq : " + summary)

        if not summary:
            raise ValueError("Summary generation failed.")

        # Cleanup: Remove the saved file after processing
        os.remove(file_path)
        
        # Return the result as a dictionary
        output = {
            'transcription': transcription,
            'summary': summary
        }
        
        print(output)
        return output

    except Exception as e:
        print(f"Error in processing voice: {e}")  # Debug: Log the error
        return {"error": str(e)}

def summarize_groq_ollama(text):

    llm = ChatGroq(
    temperature=0, 
    groq_api_key='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', 
    model_name="llama-3.1-70b-versatile")

    response = llm.invoke(text)
    return response.content

def transcribe_and_translate_audio_with_groq(audio_file, target_language="en", api_key="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"):
    """
    Transcribes and translates audio from any language to the specified target language using Whisper in Groq Cloud.
    
    Parameters:
        audio_file (str): Path to the audio file to be processed.
        target_language (str): Target language for translation. Default is English ("en").
        api_key (str): Groq API key for authentication.

    Returns:
        dict: Contains transcription and/or translation results or error details.
    """
    try:
        # Ensure the file exists
        audio_file_path = os.path.abspath(audio_file)
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        headers = {
            'Authorization': f'Bearer {api_key}'
        }

        # Transcription endpoint
        transcription_url = "https://api.groq.com/openai/v1/audio/transcriptions"

        # Translation endpoint
        translation_url = "https://api.groq.com/openai/v1/audio/translations"

        # Prepare the file for upload
        with open(audio_file_path, 'rb') as file:
            files = {
                'file': (os.path.basename(audio_file_path), file, 'audio/mpeg'),
                'model': (None, 'whisper-large-v3')
            }

            # Step 1: Transcription
            transcription_response = requests.post(transcription_url, headers=headers, files=files)
            if transcription_response.status_code != 200:
                raise Exception(f"Transcription failed: {transcription_response.text}")

            transcription_data = transcription_response.json()
            transcription = transcription_data.get("text")
            if not transcription:
                raise Exception("No transcription text found in response.")

            print(f"Transcription completed: {transcription}")

            # Step 2: Translation
            # Re-upload the file for translation if required
            file.seek(0)  # Reset file pointer for re-upload

            translation_response = requests.post(translation_url, headers=headers, files=files)
            if translation_response.status_code != 200:
                raise Exception(f"Translation failed: {translation_response.text}")

            translation_data = translation_response.json()
            translation = translation_data.get("text")
            if not translation:
                raise Exception("No translation text found in response.")

            print(f"Translation completed: {translation}")

            # Properly construct the final result
            # result = {
            #     "transcription": transcription,
            #     "translation": translation
            # }
            print(translation)
            return translation

    except Exception as e:
        print(f"Error during transcription or translation: {str(e)}")
        return {"error": str(e)}


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
