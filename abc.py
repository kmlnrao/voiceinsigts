import streamlit as st
import requests
import io

# Set the title of the Streamlit app
st.title("Real-Time Audio Capture and Transcription")

# Instruction for the user
st.write("Upload your audio file.")

# Use Streamlit file uploader for audio file input
audio_file = st.file_uploader("Upload Your Audio", type=["wav", "mp3"])

if audio_file:
    st.write("Audio file uploaded successfully.")
    
    # Send the audio to FastAPI backend for processing
    try:
        with st.spinner("Processing your audio..."):
            # Convert file to a byte stream for the API call
            audio_data = audio_file.read()
            
            # Send the audio to FastAPI as a file object
            response = requests.post(
                "http://localhost:8000/process_voice",
                files={"file": io.BytesIO(audio_data)}
            )
            result = response.json()

            if 'error' in result:
                st.error(f"Error: {result['error']}")
            else:
                transcription = result.get("transcription", "")
                summary = result.get("summary", "")
                st.subheader("Transcription:")
                st.write(transcription)
                st.subheader("Summary:")
                st.write(summary)
    except Exception as e:
        st.error(f"Error processing the audio: {e}")
