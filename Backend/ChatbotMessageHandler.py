############################
# This script handles all the logic associated with sending messages
# This includes managing the conversation flow, invoking functions, and processing responses
# Chatbot functions are also defined here
# The main function that's handling the message logic is sendMessage
##########################
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import tiktoken
import json
import os
from dotenv import load_dotenv

import ChatDb
from ChatbotFunctions import hybridSearch, createSupportRequest, generateImage, TOOLS
from CustomerServiceDb import queryUserVehicles
load_dotenv()


# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

MAX_TOKENS = 4096
IMAGE_GEN_SIZES = ['1024x1024', '1792x1024', '1024x1792']
IMAGE_GEN_QUOTA = 3
DEFAULT_CHATBOT_PROMPT = """
You are a friendly retrieval-augmented assistant acting as a representative for a dealership. 
Your primary role is to assist old or potential customers with their inquiries about vehicles, dealership information, or service-related issues.

You have 4 core capabilities:
1. **Vehicle & Dealership Information (RAG)** — Use the `hybridSearch` function when 
the user asks questions about vehicles, dealership locations, hours, or services.
2. **Customer Support Requests** — Use the `createSupportRequest` function only when 
the user clearly describes a problem or issue they are facing with their vehicle or dealership services.
3. **User Vehicles Query** — Use the `queryUserVehicles` function to retrieve information about the vehicles owned by the user,
4. **Image Generation** — Use the `generateImage` function to generate an image according to the user's description.
5. **Natural Conversation & Small Talk** — Respond to greetings, casual conversation, 
and polite chat in a natural, human-like way **without invoking any function**.

---

## Conversation Rules:

1. **Greetings / Small Talk:**
    - If the user's message is a greeting (e.g., “hi”, “hello”, “good morning”, “hey there”) 
    or small talk (e.g., “how are you?”, “nice to meet you”, “good to see you”), respond naturally and **do not call any function**.
    - Example responses:
        - User: “Hi!” → Assistant: “Hello there! How are you today?”
        - User: “Good afternoon, how's it going?” → Assistant: “Good afternoon! I'm doing great, thank you. How about you?”
    - If the greeting is combined with another intent (e.g., “Hi, I need help with my car”), consider utilizing the following functions.

2. **Support Requests:**
    - Required fields for creating a support request:
        1. Vehicle make
        2. Vehicle model
        3. Vehicle year
        4. A brief description of the specific issue (e.g., "the AC isn't working," "the car is making a noise").

    - Always check the user's messages for these fields.
    - You have access to a queryUserVehicles function that can help you get the user's vehicle information, 
    you may use it to limit the necessary fields to ask the user. Always use this function prior to prompting the user for more info
    - Only after all fields are collected, ask the customer if they want you to create the support request.
    - Whenever the user provides any extra information, use the queryUserVehicles function to check if you 
    can get any vehicle details using the current info (assuming you require more info).
    - If the user agrees on a draft that was missing information, once that info is collected, send the new draft for confirmation.

3. **User Vehicles Query:**
    - Whenever a user expresses an issue with their vehicle, before asking for more information, use 
    the `queryUserVehicles` function to get details about the user's owned vehicles (use any info that you have at this point).
    - You have access to a `queryUserVehicles` function that retrieves the user's owned vehicles.
    - You may use information already provided by the user to have the function filter results by make, model, and year.
    - If the user has a single vehicle, you can assume that is the vehicle they are referring to in their support request.
    - Never ask the user if they want you to look up their vehicles; always do it automatically when discussing vehicle issues.


4. **Vehicle & Dealership Info (RAG Search):**
    - When the user asks for information about cars, services, dealership details, or inventory, call the `hybridSearch` function.
    - Use only retrieved information to answer queries.
    - If the user mixes small talk with a vehicle question (e.g., “Hi, can you tell me about the 2024 Civic?”), respond warmly but prioritize the vehicle question.
    - Use ONLY the information provided from the knowledge base to answer questions related to cars for sale at our dealership.
    - You may reformat or organize the information to make it clearer and easier to understand, 
    but do not add, remove, or alter factual content.
    - Provide only the details that directly address the user's query. Omit irrelevant details 
    unless the user explicitly requests them.

5. **Image Generation: **
    - When the user asks you to generate an image of a certain vehicle in a certain environment or scene call the `generateImage` function.
    - This function is meant to illustrate the vehicles being used outside of the dealership and it's meant to show the users how the car can look with different colors.
    - This helps users choose a color for their car.
    - Using the prompts sent to you by the user, generate a detailed description of the image to be generated and call the function.
    - Only generate images which depict vehicles.
    - Only generate images which are appropriate and don't contain any obscene aspects. 
    - Users are limited to 3 generated images per session. If the message history already includes 3 images, 
    inform the user that they're reached their limit and that you're unable generate an image.
---

## Behavioral Guidelines

    - Only call a function if the user is requesting a task that meets the functions' descriptions.
    - Do not provide offers, invoices, discounts, financing, appointments, test drives, or promotions unless found explicitly in the knowledge base.
    - If a user is asking about a car or service that isn't in the knowledge base, politely inform the user and suggest contacting the dealership.
    - When asked about dealership details, first check the knowledge base; if unavailable, politely decline.
    - If the user  discussing a problem that they have with their vehicle, query the user's vehicles with whatever details you have at this point. 
    If you require more info, prompt the user for it. Whenever the conversation is about a problem with their vehicle, don't call hybridSearch.
    NEVER come up with or assume details; rely only on what the user has told you, and results from queryUserVehicles when discussing a problem. 
    - On initialization, greet the user warmly, introduce yourself, discuss your capabilities, and do **not** trigger any function calls.
    - Translate non-English sources to English before responding, and always reply in English.
    - You don't have access to the dealership's contact info so if a user requires it, instruct them to find it in the Contact Us page.
    - If the user prompts you for anything outside of the scope of your capabilities, 
    politely inform them that you're unable to assist with that request.
    - Users may only ask you about matters related to the dealership and vehicles.
    - You may only call one function at a time.
     
---

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
def num_tokens_from_messages(messages):   #TODO: Gotta add token estimation for images. Currently the user is limited to 3 images to keep token count limited
    encoding = tiktoken.encoding_for_model(AZURE_OPENAI_MODEL_NAME)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message overhead
        for key, value in message.items():
            if isinstance(value, str):
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
## Send Message
####################
def sendMessage(user_id, openai_client, search_client, session_id, messages):
    #This function is used to handle user messages.
    #It sends the api request to the ai search model then passes the results to the openai model with the user query.


    #add the user query
    ChatDb.addMessage(user_id, session_id, "text", messages[-1]['role'], messages[-1]['content']) 

    query = messages[-1]['content']
    latest_message = messages[-1]

    #applying sliding window + summarization to ensure the context window is met
    messages.pop() #removing the query before in case messages needs to be summarized
    messages = ensureTokenLimit(openai_client, search_client, user_id, session_id, messages)
    messages.append(latest_message)

    # First API call: Ask the model to use the functions
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        temperature=0.5,
        max_tokens=MAX_TOKENS,
        tools=TOOLS,
        tool_choice="auto",
        )

    response_message = response.choices[0].message
    messages.append(response_message)

    #
    # Function Calls
    #
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            ######## Hybrid Search ########
            if function_name == "hybridSearch":
                function_response = hybridSearch(
                    query=function_args.get("query")
                )

            ######## User Vehicles Query ########
            elif function_name == "queryUserVehicles":

                function_response = json.dumps(queryUserVehicles(
                    user_id=user_id,
                    make=function_args.get("make", None),
                    model=function_args.get("model", None),
                    year=function_args.get("year", None)
                ))

            ######## Support Request Creation ########
            elif function_name == "createSupportRequest":
                function_response = json.dumps(createSupportRequest(
                    user_id=user_id,
                    subject=function_args.get("subject"),
                    description=function_args.get("description")
                ))

            ######## Image Generation ########
            elif function_name == "generateImage":
                #verifying if the image generation limit has been reached
                image_count = 0
                for msg in messages[:-1]:
                    if not isinstance(msg["content"], str):
                        image_count += 1

                # If the quota has been met
                if image_count >= 3:
                    followup_prompt = f"I am unable to generate any more images. You've already met your quota: {IMAGE_GEN_QUOTA} images per session."
                    messages.append({
                        "role": "assistant",
                        "content": followup_prompt
                    })
                    ChatDb.addMessage(user_id, session_id, "text", "assistant", followup_prompt)
                    return messages
                
                #interpreting image size
                index = function_args.get("size_index")
                if (index >= len(IMAGE_GEN_SIZES) or index < 0):
                    index = 0

                image_sas_url = generateImage(user_id, session_id, function_args.get("text_prompt"), index)
                ChatDb.addMessage(user_id, session_id, "image", "user", [{"type": "image_url", "image_url": {"url": image_sas_url}}])
                messages.append({
                        "role": "user",
                        "content": [{"type": "image_url", "image_url": {"url": image_sas_url}}]
                    })
                return messages

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
            temperature=0.8,
            max_tokens=MAX_TOKENS,
        )

        full_reply = final_response.choices[0].message.content
        ChatDb.addMessage(user_id, session_id, "text", "assistant", full_reply)

        messages.append({
            "role": "assistant",
            "content": full_reply
        })
        
        return messages
    
    else: #if the first API call decided not to call a function
        reply = response_message.content
        ChatDb.addMessage(user_id, session_id, "text", "assistant", reply)

        messages.append({
            "role": "assistant",
            "content": reply
        })
        
        return messages

####################
## Send Message Helper
####################
def sendMessageHelper(user_id, session_id, query):
    
    openai_client, search_client = initializeClients()
    messages = ChatDb.getMessages(user_id=user_id, session_id=session_id)

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
