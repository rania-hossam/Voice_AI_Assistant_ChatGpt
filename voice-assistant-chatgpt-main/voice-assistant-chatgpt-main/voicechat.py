import streamlit as st
import whisper
import openai
from audiorecorder import audiorecorder
import magic
import os
import re

def generate_voice(text, voice):
    """Generates Text-To-Speech voice using the Web Speech API."""

    js_code = f"""
        const synth = window.speechSynthesis;
        const utterance = new SpeechSynthesisUtterance("{text}");
        utterance.voice = speechSynthesis.getVoices().filter((v) => v.name === "{voice}")[0];
        synth.speak(utterance);
    """

    # Embed the JavaScript code in the web page
    st.components.v1.html(f"<script>{js_code}</script>", height=0)


def get_audio_record_format(orgfile):
    """Determines the format of the audio recording file."""

    info = magic.from_file(orgfile).lower()
    print(f'\n\n Recording file info is:\n {info} \n\n')

    if 'webm' in info:
        return '.webm'
    elif 'iso media' in info:
        return '.mp4'
    elif 'wave' in info:
        return '.wav'
    else:
        return '.mp4'


class Conversation:
    """Handles conversation with OpenAI's GPT-3 model."""

    def __init__(self, engine):
        self.engine = engine

    def generate_response(self, message):
        """Generates a response to a given message."""

        response = openai.Completion.create(
            engine=self.engine,
            prompt=message,
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.2,
            presence_penalty=0.6,
            frequency_penalty=0.6
        )

        return response.choices[0].text.strip()


@st.cache
def init_load_setups():
    """Loads necessary setups including ASR model and ChatGPT instance."""

    # Setup ASR engine
    asrmodel = whisper.load_model('base', download_root='asrmodel')

    # Setup ChatGPT instance
    openai.api_key = os.getenv("OPENAI_API_KEY").strip('"')
    conversation = Conversation(engine="text-davinci-003")

    # Load TTS voices and language code mapping
    tts_voices = {}
    for line in open('language-tts-voice-mapping.txt', 'rt').readlines():
        if len(line.strip().split(',')) == 3:
            language, lang_code, voice_name = line.strip().split(',')
            tts_voices[lang_code.strip()] = voice_name.strip()

    return asrmodel, conversation, tts_voices


def app():
    """Main voice chat application."""

    st.title("ChatGPT Voice Assistant")
    st.subheader("It understands 97 Spoken Languages!")

    # Get initial setup
    asr, chatgpt, tts_voices = init_load_setups()

    # Recorder
    audio = audiorecorder("Push to Talk", "Recording... (push again to stop)")

    if len(audio) > 0:
        # Play audio in frontend
        st.audio(audio.tobytes())

        # Save audio to a file
        audio_name = 'recording.tmp'
        with open(audio_name, "wb") as f:
            f.write(audio.tobytes())
        
        # Get record file format based on file magics
        record_format = get_audio_record_format(audio_name)
               os.rename(audio_name, audio_name + record_format)

        st.markdown("<b>Chat History</b> ", unsafe_allow_html=True)

        with st.spinner("Recognizing your voice command ..."):
            asr_result = asr.transcribe(audio_name + record_format)
            text = asr_result["text"]
            language_code = asr_result["language"]
            st.markdown("<b>You:</b> " + text, unsafe_allow_html=True)
            print('ASR result is:' + text)

        st.write('')

        with st.spinner("Getting ChatGPT answer for your command ..."):
            response = chatgpt.generate_response(text)
            st.markdown("<b>ChatGPT:</b> " + response, unsafe_allow_html=True)
            print('ChatGPT response is: '   + response)
            spoken_response = re.sub(r'\s+', ' ', response).strip()

            # Speak the input text
            generate_voice(spoken_response, tts_voices[language_code])


if __name__ == "__main__":
    app()


