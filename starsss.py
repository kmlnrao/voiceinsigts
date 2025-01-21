import streamlit as st
import sounddevice as sd
import numpy as np
import io
import requests
import wave
import time  # Import for timing

# Backend API endpoint
API_ENDPOINT = "http://localhost:8000/process_voice"

# App title
st.title("Voice Insights")

# Tabs for navigation
tab1, tab2 = st.tabs(["Real-Time Recording", "Upload Voice File"])

# Helper function to save NumPy array to WAV byte data
def save_to_wav(audio_data, sample_rate=16000):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    buffer.seek(0)
    return buffer

# Helper function to trim silence from audio
def trim_silence(audio, threshold=100, sample_rate=16000):
    audio_flat = audio.flatten()
    # Identify regions where audio magnitude exceeds the threshold
    non_silent_indices = np.where(abs(audio_flat) > threshold)[0]
    if len(non_silent_indices) == 0:
        return audio  # No trimming if all silent
    start_index = non_silent_indices[0]
    end_index = non_silent_indices[-1]
    return audio[start_index:end_index + 1]

# Initialize session state
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "audio_data" not in st.session_state:
    st.session_state.audio_data = None
if "recording_ready" not in st.session_state:
    st.session_state.recording_ready = False

with tab1:
    st.header("Real-Time Voice Recording")

    # "Speak Now" button
    if st.button("Speak Now"):
        # Reset the state and clear any previous audio data
        st.session_state.audio_data = None
        st.session_state.recording_ready = False

        if not st.session_state.is_recording:
            st.session_state.is_recording = True

            # Start recording in the background
            duration = 30  # Allow recording for up to 10 seconds
            sample_rate = 16000
            st.session_state.audio_data = sd.rec(
                int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16"
            )
            st.info("Recording audio... Speak now and press 'Stop Recording' to finish.")

    # "Stop Recording" button
    if st.session_state.is_recording and st.button("Stop Recording"):
        st.session_state.is_recording = False
        sd.stop()

        # Finalize the recording and process the audio
        if st.session_state.audio_data is not None:
            trimmed_audio = trim_silence(st.session_state.audio_data)
            st.session_state.audio_data = trimmed_audio

            st.success("Recording stopped. You can now upload the audio.")
            st.session_state.recording_ready = True

            # Convert to WAV and preview the trimmed audio
            wav_file = save_to_wav(trimmed_audio)
            st.audio(wav_file, format="audio/wav")

    # "Upload Audio" button
    if st.session_state.recording_ready:
        if st.button("Upload Audio"):
            st.info("Submitting audio to the backend...")

            if st.session_state.audio_data is not None:
                wav_file = save_to_wav(st.session_state.audio_data)
                files = {
                    "file": ("voice-recording.wav", wav_file, "audio/wav")
                }

                try:
                    start_time = time.time()  # Start timing
                    response = requests.post(API_ENDPOINT, files=files)
                    elapsed_time = time.time() - start_time  # Calculate elapsed time

                    if response.status_code == 200:
                        response_data = response.json()
                        st.success("Transcription and Summary received!")
                        st.write("**Transcription:**", response_data.get("transcription", "No transcription received."))
                        st.write("**Summary:**", response_data.get("summary", "No summary received."))
                        st.info(f"Processing completed in {elapsed_time:.2f} seconds.")
                    else:
                        st.error(f"Error in API response: {response.status_code}")
                except Exception as e:
                    st.error(f"Error sending request: {e}")

            # Clear the audio data after uploading
            st.session_state.audio_data = None
            st.session_state.recording_ready = False
    else:
        st.warning("Please record audio first.")

with tab2:
    st.header("Upload Voice File")

    # File upload
    uploaded_file = st.file_uploader("Choose a voice file", type=["wav", "mp3", "m4a", "ogg"])
    if uploaded_file is not None:
        st.audio(uploaded_file, format="audio/wav")

        # Upload audio file to the backend
        if st.button("Submit File"):
            with st.spinner("Processing..."):
                # Read the file content
                audio_data = uploaded_file.read()

                # Prepare the files dictionary
                files = {
                    "file": (uploaded_file.name, audio_data, uploaded_file.type)
                }

                try:
                    start_time = time.time()  # Start timing
                    response = requests.post(API_ENDPOINT, files=files)
                    elapsed_time = time.time() - start_time  # Calculate elapsed time

                    response_data = response.json()

                    st.success("Transcription and Summary received!")
                    st.write("**Transcription:**", response_data.get("transcription", "No transcription received."))
                    st.write("**Summary:**", response_data.get("summary", "No summary received."))
                    st.info(f"Processing completed in {elapsed_time:.2f} seconds.")
                except Exception as e:
                    st.error(f"Error: {e}")
