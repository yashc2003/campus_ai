# Voice assistant

The Voice Assistant records in Streamlit or accepts an audio file, transcribes it locally with Whisper, then runs the same intent and source retrieval steps as text input. Install `requirements-voice.txt`; it includes a bundled FFmpeg runtime. Choose Tiny, Base, or Small; the selected Whisper checkpoint downloads once on first use. Audio is not sent to an external API by this project.

Multilingual transcription depends on the Whisper model and microphone/audio quality. It has not been benchmarked on this dataset.
