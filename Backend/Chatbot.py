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
You are a friendly retrieval-augmented assistant acting as a car salesman for a dealership.

Guidelines:
- You are in a marketing and sales role. Do NOT provide offers, discounts, invoices, or pricing beyond the listed price.
- If asked about offers, politely refuse and inform the customer that they must contact the dealership for such details.
- Use ONLY the provided sources to answer queries, in a friendly and concise manner. 
- You may format the info differently than it is in the source as long as the content is the same.
- If there is not enough information, say you don't know and guide the user to ask questions within your scope.
- If sources are in Arabic, translate them into English before responding.
- You may only generate responses in English.

Conversation rules:
- Every message will have the format:
  query: <user query>
  sources: \n<formatted list of sources>
- Exception: If asked to summarize the conversation, use ONLY the conversation history.
- On initialization, greet the user warmly and introduce yourself.
- For greetings, small talk, or questions like "how are you," respond naturally like a friendly salesman (ignore sources).

Remember: Stay professional, helpful, and upbeat — like a real car salesman who knows the vehicles inside out.
"""


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
    #It returns the new/old messages list. If summarized, the message list is only returned with 
    # the summary not the summarization prompt
    
    if num_tokens_from_messages(messages) >= MAX_TOKENS* 0.8 and len(messages)>2:

        summary_prompt = "Summarize the conversation so far in a concise manner, retaining important details and context. " \
        "The summary should be brief and to the point, capturing the essence of the discussion without unnecessary elaboration. " \
        "The summary will be used to maintain context in future interactions, so ensure it is clear and informative."

        messages.append({
            "role": "user",
            "content": summary_prompt
        })

        response = openai_client.chat.completions.create(
            stream=False,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.75,
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        )
        full_reply = response.choices[0].message.content
        messages.pop() #removing the summary prompt
        messages.append({
            "role": "assistant",
            "content": full_reply
        }) 


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
    query: {query}, 
    sources:\n{sources}
    """ 
    query = messages[-1]['content']
    latest_message = messages[-1]

    #applying sliding window + summarization to ensure the context window is met
    messages.pop() #removing the query before in case messages needs to be summarized
    messages = ensureTokenLimit(openai_client, search_client, user_id, session_id, messages)
    messages.append(latest_message)

    if rag: #apply rag. typically used for user messages (to be ignored for the first system prompt)

        #embedding the query
        embed_query = openai_client.embeddings.create(
            input=query,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        ).data[0].embedding

        vector_query = VectorizedQuery(
                vector=embed_query,
                k_nearest_neighbors=5,
                fields="content_vector",
                kind="vector",
                exhaustive=True
            )

        search_results = search_client.search(
                    include_total_count=True,
                    search_text=query,  
                    select="id, chunk, file_name, page_number, chunk_index, parent_id",
                    top=5,
                    vector_queries=[vector_query]
                )

        #fetchin neighbouring chunks (Contextual expansion)
        window= 1 #how many neighbouring chunks do we take from each direction
        expanded_results = []
        ids_in_expanded_results = []
        for doc in search_results:

            if doc["id"] not in ids_in_expanded_results:
                expanded_results.append(doc)
                ids_in_expanded_results.append(doc["id"])

            parent_id = doc["parent_id"]
            chunk_index = doc["chunk_index"]
            neighbor_filter = f"parent_id eq '{parent_id}' and chunk_index ge {chunk_index - window} and chunk_index le {chunk_index + window}"

            neighbors = search_client.search(
                search_text="*",
                filter=neighbor_filter,
                select="id, chunk, file_name, page_number, chunk_index, parent_id"
            )

            for n in neighbors:
                if n["id"] != doc["id"] and n["id"] not in ids_in_expanded_results: 
                    expanded_results.append(n)
                    ids_in_expanded_results.append(n["id"])

        #formatting results to pass to model
        sources_formatted = "\n\n".join([
            f"chunk: {doc['chunk']}\n"
            f"file_name: {doc['file_name']}\n"
            f"page_number: {doc['page_number']}\n"
            f"chunk_index: {doc['chunk_index']}\n"
            for doc in expanded_results
        ])

        messages[-1]["content"] = grounded_prompt.format(query=query, sources=sources_formatted)

    full_reply = ""
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.8,
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
    
    openai_client, search_client = initializeClients()
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
    openai_client.close()
    return reply


def listMessages(user_id, session_id):
        return Database.getMessages(user_id=user_id, session_id=session_id)

def createSession(user_id, session_name):

    new_session_id = Database.addSession(user_id, session_name)
    openai_client, search_client = initializeClients()

    messages = [
                {
                    "role": "system",
                    "content": DEFAULT_CHATBOT_PROMPT
                }
            ]
    messages = sendMessage(user_id, openai_client, search_client, new_session_id, messages, False)
    openai_client.close()
    return new_session_id


def clearChat(user_id, session_id):

    openai_client, search_client = initializeClients()
    messages = Database.getMessages(user_id=user_id, session_id=session_id)

    messages = [
        {
            "role": "system",
            "content": DEFAULT_CHATBOT_PROMPT
        }
    ]
    Database.clearSession(user_id=user_id, session_id=session_id)
    messages = sendMessage(user_id, openai_client, search_client, session_id, messages, False)
    openai_client.close()
    return messages

        

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
    