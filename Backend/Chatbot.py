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

Conversation Rules:
- You are in a marketing and sales role. Do NOT provide offers, discounts, invoices, or pricing beyond the listed price.
- If asked about offers, politely refuse and inform the customer that they must contact the dealership for such details.
- When asked about information related to vehicles, call the hybridSearch function to retrieve relevant documents from the knowledge base.
- Use ONLY the information provided from the knwoeldge base to answer queries, in a friendly and concise manner. 
- You may format and present the info differently than it is in the source to make it clearer and more organized
 as long as you don't add or alter the content. You may also give the user part of the information from the search 
 results if some parts are not relavant to the query.
- If there is not enough information or if you are asked about something outside your specified scope, 
say you don't know and guide the user to ask questions within your scope.
- If a vehicle isn't in the knowledge base, then the dealership does not have it. Politely inform the user of 
this and have them contact the dealer to ask for more details.


Behavior:
- Every messages should use the knowledge base to provide accurate and relevant information except in a few specific scenarios.
- Exception: If asked to summarize the conversation, use ONLY the conversation history.
- Exception: If the user is sending a greeting, asking you how are you, or making minor small 
talk you may reply as a normal person (and salesperson) would reply (don't call the hybridSearch function).
- When engaging in small talk, you may use a more casual and friendly tone, but always maintain professionalism 
and keep the context within greetings and introductions.
- On initialization, greet the user warmly and introduce yourself. 
- If sources are in Arabic, translate them into English before responding.
- You may only generate responses in English.


Remember: Stay professional, helpful, and upbeat — like a real car salesman who knows the vehicles inside out.
"""


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

####################
## Token Counter
####################
def num_tokens_from_messages(messages):
    encoding = tiktoken.encoding_for_model(AZURE_OPENAI_MODEL_NAME)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message overhead
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
    num_tokens += 2  # every reply overhead
    return num_tokens

####################
## Ensuring Token Limit
####################
def ensureTokenLimit(openai_client, search_client, user_id, session_id, messages):
    #This function checks if the token limit is almost reached and if so performs a combination of sliding window and summarization
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

####################
## Hybrid Search
####################
def hybridSearch(query):
    #This function is used to perform a hybrid search on the search index with context expansion
    #It returns the search results

    #embedding the query
    openai_client, search_client = initializeClients()
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

    return json.dumps({"vector_search_results": sources_formatted})
    

####################
## Send Message
####################
def sendMessage(user_id, openai_client, search_client, session_id, messages):
    #This function is used to handle user messages.
    #It sends the api request to the ai search model then passes the results to the openai model with the user query.


    #add the user query
    Database.addMessage(user_id, session_id, messages[-1]['role'], messages[-1]['content']) 

    query = messages[-1]['content']
    latest_message = messages[-1]

    #applying sliding window + summarization to ensure the context window is met
    messages.pop() #removing the query before in case messages needs to be summarized
    messages = ensureTokenLimit(openai_client, search_client, user_id, session_id, messages)
    messages.append(latest_message)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "hybridSearch",
                "description": "Performs hybrid search on the search index to retrieve relevant documents. Useful for when you need to find relevant information in the knowledge base to answer the query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user prompt that was sent to the chat completion model. It the last user message.",
                        },
                    },
                    "required": ["query"],
                },
            }
        }
    ]

    # First API call: Ask the model to use the functions
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.8,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        tools=tools,
        tool_choice="auto",
        )

    response_message = response.choices[0].message
    messages.append(response_message)

    # Handle function calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "hybridSearch":
                function_response = hybridSearch(
                    query=function_args.get("query")
                )
            else:
                function_response = json.dumps({"error": "Unknown function"})
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            })

    # Second API call: Get the final response from the model
    final_response = openai_client.chat.completions.create(
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        messages=messages,
        max_tokens=MAX_TOKENS,
    )

    full_reply = final_response.choices[0].message.content
    Database.addMessage(user_id, session_id, "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
    
    return messages

####################
## Send Message Helper
####################
def sendMessageHelper(user_id, session_id, query):
    
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
    )
    
    reply = updated_messages[-1]["content"]
    openai_client.close()
    return reply

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
        temperature=0.8,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        )

    full_reply = response.choices[0].message.content

    Database.addMessage(user_id, session_id, messages[-1]['role'], messages[-1]['content']) 
    Database.addMessage(user_id, session_id, "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
        
    openai_client.close()
    return messages


def listMessages(user_id, session_id):
        return Database.getMessages(user_id=user_id, session_id=session_id)

###################
## Create Session
###################
def createSession(user_id, session_name):

    new_session_id = Database.addSession(user_id, session_name)
    initializeChat(user_id, new_session_id)
    return new_session_id


###################
## Clear Chat
###################
def clearChat(user_id, session_id):

    Database.clearSession(user_id=user_id, session_id=session_id)
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
    