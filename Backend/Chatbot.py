import azure.identity
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
import azure.cognitiveservices.speech as speechsdk

from openai import AzureOpenAI
import tiktoken
import json
import os
import requests

import Database

# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
AZURE_SPEECH_TO_TEXT_ENDPOINT = os.getenv("AZURE_SPEECH_TO_TEXT_ENDPOINT")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

MAX_TOKENS = 3000
DEFAULT_CHATBOT_PROMPT = """
    You are a friendly retrieval-augmented assistant that serves as a car salesman for a dealership.
    You are in a marketing and sales role, but you cannot give the customer any offers or discounts.
    If the customer asks for offers, invoices or anything related to pricing, you should politely refuse 
    and inform them that you are not authorized to provide such information. You may only give them the listed 
    price of the vehicle and inform them that they can contact the dealership for any offers or discounts.
    Answer the query using only the sources provided in each query in a friendly and concise manner.
    If there isn't enough information below, say you don't know and tell the user to ask questions related to your scope.
    Every message will have the following format:
    query: <user query>, sources:\n<formated list of sources>
    The only exception to this format is when you are asked to summarize the conversation. 
    In this case, rely only on the conversation history.
    Once Initialized, greet the user with a welcome message and introduce yourself.
    If the user is sending a greeting, asking you how are you, or making minor small talk you may reply 
    like a friendly salesman (ignore the sources provided).
    If any of the provided sources are in Arabic, translate them before relaying them to the user. 
    You may only generate responses in English.
    """

def initializeClients(user_id):
   
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

def num_tokens_from_messages(messages):
    encoding = tiktoken.encoding_for_model(AZURE_OPENAI_MODEL_NAME)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message overhead
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
    num_tokens += 2  # every reply overhead
    return num_tokens

def ensureTokenLimit(openai_client, search_client, user_id, session_id, messages):
    #This function checks if the token limit is almost reached
    #If the limit is almost reached, it summarizes the conversation and creates a new messages list
    #It returns the new/old messages list
    
    if num_tokens_from_messages(messages) >= MAX_TOKENS* 0.8:

        summary_prompt = "Summarize the conversation so far in a concise manner, retaining important details and context. " \
        "The summary should be brief and to the point, capturing the essence of the discussion without unnecessary elaboration. " \
        "The summary will be used to maintain context in future interactions, so ensure it is clear and informative."

        messages.append({
            "role": "user",
            "content": summary_prompt
        })

        messages = sendMessage(user_id, openai_client, search_client, session_id, messages, False) 

        #last 5 messages + summary will be kept in history. 
        #The rest of the messages will be displayed but not stored within the context window
        if(len(messages) > 10):
            summary_messages = messages[:2] + messages[-7:] 

        else:
            summary_messages = messages[:2] + messages[-2:] #only keep the summary and the system prompt 

        return summary_messages
    
    else:
        return messages


def sendMessage(user_id, openai_client, search_client, session_id, messages, rag=True):
    #This function is used to handle user messages.
    #It sends the api request to the ai search model then passes the results to the openai model with the user query.
    # and prints the response as it's being generated

    grounded_prompt = """
    Provide an answer to this query while referring to the sources provided. Answer ONLY in english (translate the source if need be). 
    If the user is sending a greeting, asking you how are you, or making minor small talk you may reply 
    like a friendly salesman (ignore the sources provided).\n
    query: {query}, sources:\n{sources}
    """ 
    query = messages[-1]['content']

    if rag: #apply rag. typically used for user messages (except for summarization)

        #embedding the query
        embed_query = openai_client.embeddings.create(
            input=query,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        ).data[0].embedding

        vector_query = VectorizedQuery(
                vector=embed_query,
                k_nearest_neighbors=5,
                fields="text_vector",
                kind="vector",
                exhaustive=True
            )

        #retrieving documents (hybrid search)
        search_results = search_client.search(
                    include_total_count=True,
                    search_text=query,  
                    select="brand,model,type,year,price,chunk,features",
                    top=5,
                    vector_queries=[vector_query]
                )

        sources_formatted = "\n\n".join([
            f"Brand: {doc['brand']}\n"
            f"Model: {doc['model']}\n"
            f"Type: {doc['type']}\n"
            f"Year: {doc['year']}\n"
            f"Price: {doc['price']}\n"
            f"Description: {doc['chunk']}\n"
            f"Features: {', '.join(doc.get('features') or [])}"
            for doc in search_results
        ])

        messages[-1]["content"] = grounded_prompt.format(query=query, sources=sources_formatted)

    full_reply = ""
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.75,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    )

    full_reply = response.choices[0].message.content

    #replace the last user message with the original query (without sources in the case of RAG)
    messages[-1]["content"] = query

    #typically the last message is the user's message but sometimes it could be a system message
    Database.addMessage(user_id, session_id, messages[-1]['role'], messages[-1]['content']) 
    Database.addMessage(user_id, session_id, "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
    
    return messages

def sendMessageHelper(user_id, session_id, query, rag):
    
    try:
        openai_client, search_client = initializeClients(user_id)
        messages = Database.getMessages(user_id=user_id, session_id=session_id)

        messages.append({
            "role": "user",
            "content": query
        })

        # Call your existing function
        updated_messages = sendMessage(
            user_id=user_id,
            openai_client=openai_client,
            search_client=search_client,
            session_id=session_id,
            messages=messages,
            rag=rag
        )
        
        reply = updated_messages[-1]["content"]
        ensureTokenLimit(openai_client, search_client, user_id, session_id, updated_messages)
        
        return reply
    
    finally:
        openai_client.close()

def listMessages(user_id, session_id):
        return Database.getMessages(user_id=user_id, session_id=session_id)

def createSession(user_id, session_name):
    try:
        new_session_id = Database.addSession(user_id, session_name)
        openai_client, search_client = initializeClients(user_id)

        messages = [
                    {
                        "role": "system",
                        "content": DEFAULT_CHATBOT_PROMPT
                    }
                ]
        messages = sendMessage(user_id, openai_client, search_client, new_session_id, messages, False)
        return new_session_id
    except:
        return None

    finally:
        openai_client.close()

def clearChat(user_id, session_id):
    try:
        openai_client, search_client = initializeClients(user_id)
        messages = Database.getMessages(user_id=user_id, session_id=session_id)

        messages = [
            {
                "role": "system",
                "content": DEFAULT_CHATBOT_PROMPT
            }
        ]
        Database.clearSession(user_id=user_id, session_id=session_id)
        messages = sendMessage(user_id, openai_client, search_client, session_id, messages, False)
        return messages
    finally:
        openai_client.close()

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
    