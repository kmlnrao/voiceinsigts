from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import requests
import json

app = FastAPI() 

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific domains in production
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/process_voice")

async def process_voice(file: UploadFile = File(...)):
    file_path = os.path.abspath(f"./{file.filename}")  # Use absolute path for better file handling
    print(f"Saving file: {file_path}")  # Debug: Check file path

    try:
        # Save the uploaded file to the local directory
        with open(file_path, "wb") as audio_file:
            audio_file.write(await file.read())
        print(f"File {file.filename} saved successfully at {file_path}")  # Debug: Confirm file is saved
        
        transcription = transcribe_audio(file_path)
        if not transcription:
            raise ValueError("Transcription failed.")
        print(f"Transcription: {transcription} ")  # Debug: Check transcription
        
        summary = summarize_with_ollama(transcription + " Summaries")
        if not summary:
            raise ValueError("Summary generation failed.")
        print(f"Summary: {summary}")  # Debug: Check summary

        # Cleanup: Remove the saved file after processing
        os.remove(file_path)

        return {"transcription": transcription, "summary": summary}
    
    except Exception as e:
        print(f"Error in processing voice: {e}")  # Debug: Log the error
        return {"error": str(e)}

# def transcribe_audio(audio_file):
    try:
        # Get absolute path and normalize it
        audio_file_path = os.path.abspath(audio_file)
        print(f"Transcribing file: {audio_file_path}")
        
        # Ensure file exists before proceeding
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")
        
        # Run whisper command
        result = subprocess.run(
            ["whisper", audio_file_path, "--model", "base"],
            capture_output=True,
            text=True,
            shell=True  # Use shell on Windows for better path handling
        )
        
        # Check for errors
        if result.returncode != 0:
            raise Exception(f"Whisper failed: {result.stderr}")
        
        # Debugging output
        print(f"Whisper STDOUT: {result.stdout}")
        print(f"Whisper STDERR: {result.stderr}")
        
        # Parse transcription from output
        transcription = result.stdout.split("\n")[-2].strip()  # Get second-last line
        return transcription
    
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def transcribe_audio(audio_file):
    try:
        audio_file_path = os.path.abspath(audio_file)
        print(f"Transcribing file: {audio_file_path}")
        
        # Ensure file exists before proceeding
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")
        
        # Define output directory
        output_dir = os.path.dirname(audio_file_path)
        output_format = "txt"
        
        # Run whisper command
        result = subprocess.run(
            [
                "whisper", audio_file_path, "--model", "base",
                "--output_dir", output_dir, "--output_format", output_format
            ],
            capture_output=True,
            text=True,
            shell=True  # Use shell=True for Windows
        )
        
        if result.returncode != 0:
            raise Exception(f"Whisper failed: {result.stderr}")
        
        # Debugging output
        print(f"Whisper STDOUT: {result.stdout}")
        print(f"Whisper STDERR: {result.stderr}")
        
        # Read transcription from generated file
        transcription_file = os.path.join(
            output_dir, f"{os.path.basename(audio_file_path).split('.')[0]}.txt"
        )
        
        if os.path.exists(transcription_file):
            with open(transcription_file, "r", encoding="utf-8") as file:
                transcription = file.read().strip()
            return transcription
        else:
            raise FileNotFoundError(f"Transcription file not found: {transcription_file}")
    
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

    
def summarize_with_ollama(text):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3:latest",
        "prompt": text
    }
    headers = {"Content-Type": "application/json"}

    try:
        # Make the POST request with streaming enabled
        response = requests.post(url, json=payload, headers=headers, stream=True)
        print(f"Response status code: {response.status_code}")  # Debug: Check the status code
        
        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")

        # Initialize an empty string to hold the final response
        full_response = ""

        # Process the response line by 
        for line in response.iter_lines():
            if line:  # Avoid empty lines
                try:
                    chunk = json.loads(line)  # Parse each line as JSON
                    full_response += chunk.get("response", "")  # Append "response" field
                except json.JSONDecodeError as e:
                    print("JSON Parse Error:", e, "Line:", line)
        
        if not full_response:
            raise Exception("No valid response from Ollama API.")
        
        return full_response  # Return the full response

    except Exception as e:
        print(f"Error with Ollama API: {e}")  # Debug: Log Ollama errors
        return None


@app.get("/")
def root():
    return {"message": "Doctor-Patient Voice Processing Backend"}
