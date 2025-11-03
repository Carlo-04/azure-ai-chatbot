######################
# This script contains helper functions for the chatbot server
# They handle general tasks such as initializing clients, managing chat sessions, and processing audio
# All Message handling logic should be in ChatbotMessageHandler.py
######################
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import azure.cognitiveservices.speech as speechsdk

from openai import AzureOpenAI
import os
import requests
from dotenv import load_dotenv

import ChatDb
from ChatbotMessageHandler import DEFAULT_CHATBOT_PROMPT
load_dotenv()


# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_IMAGE_GEN_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_IMAGE_GEN_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
AZURE_SPEECH_TO_TEXT_ENDPOINT = os.getenv("AZURE_SPEECH_TO_TEXT_ENDPOINT")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME")

MAX_TOKENS = 4096


####################
## Client Initialization
####################
def initializeClients(): 
    openai_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )

    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
    )

    return openai_client, search_client

###################
## Initialize Chat
###################
def initializeChat(user_id, session_id):
    """
    Initializes a new chat session with a greeting message from the assistant
    Mainly used when creating a new session and clearing the session
    """
    openai_client, search_client = initializeClients()
    messages = [
                {
                    "role": "system",
                    "content": DEFAULT_CHATBOT_PROMPT
                }
            ]
    
    full_reply = ""
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.75,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        )

    full_reply = response.choices[0].message.content

    ChatDb.addMessage(user_id, session_id, "text", messages[-1]['role'], messages[-1]['content']) 
    ChatDb.addMessage(user_id, session_id, "text", "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
        
    openai_client.close()
    return messages

################
## List Messages
##############
def listMessages(user_id, session_id):
        return ChatDb.getMessages(user_id=user_id, session_id=session_id)

###################
## Create Session
###################
def createSession(user_id, session_name):

    new_session_id = ChatDb.addSession(user_id, session_name)
    initializeChat(user_id, new_session_id)
    return new_session_id


###################
## Clear Chat
###################
def clearChat(user_id, session_id):

    ChatDb.clearSession(user_id=user_id, session_id=session_id)
    messages = initializeChat(user_id, session_id)
    return messages

        
###################
## Speech To Text
###################
def transcribeAudio(file):
    """
    Sends an audio file to Azure AI Foundry Fast Transcription service
    and returns the transcript (string or JSON).
    """

    url = f"{AZURE_AI_FOUNDRY_ENDPOINT}/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_OPENAI_API_KEY,
        "Accept": "application/json"
    }

    # Attach audio + transcription definition
    files = {
        "audio": (file.filename, file.stream, file.content_type),
        "definition": (
            None,
            '{"locales":["en-US"],'
            '"profanityFilterMode":"Masked",'
            '"channels":[0,1]}',
            "application/json"
        )
    }

    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()

    response_json = response.json()
    combined_phrases = response_json.get('combinedPhrases')
    transcript = combined_phrases[0].get('text')
    # Extract text if available, else return raw JSON
    return transcript

###################
## Text To Speech
###################
def generateAudio(text):
    #Takes a string and returns the audio content as raw bytes

    endpoint = os.getenv("AZURE_TEXT_TO_SPEECH_ENDPOINT")
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_OPENAI_API_KEY, 
                                        endpoint=endpoint)
    speech_config.speech_synthesis_voice_name = "en-US-BrandonMultilingualNeural"
    
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        
        audio_stream = speechsdk.AudioDataStream(result)
        audio_bytes = bytearray()

        chunk_size = 4096
        buffer = bytes(chunk_size) 

        while True:
            size_filled = audio_stream.read_data(buffer)
            if size_filled == 0:
                break
            audio_bytes.extend(buffer[:size_filled])
        return bytes(audio_bytes)

    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        raise RuntimeError(
            f"Speech synthesis canceled: {cancellation_details.reason}, "
            f"details: {cancellation_details.error_details}"
        )
