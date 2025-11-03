#####################
# This script contains the functions used by the chatbot
# These functions are called from ChatbotMessageHandler.py
###################
from azure.search.documents.models import VectorizedQuery
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import json
import os
import re
import base64
import uuid
from dotenv import load_dotenv

import CustomerServiceDb as SupportDb
import Container

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
IMAGE_GEN_SIZES = ['1024x1024', '1792x1024', '1024x1792']
IMAGE_GEN_QUOTA = 3


TOOLS = [
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
        },    
        {
            "type": "function",
            "function": {
                "name": "queryUserVehicles",
                "description": """
                Queries the database for vehicles owned by the user.
                You can provide optional filters such as make, model, and year to narrow down the results
                Useful for when you need to know what vehicles the user owns in order to create a support request.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "This is the model of the vehicle owned by the user.",
                        },
                        "make": {
                            "type": "string",
                            "description": "This is the make of the vehicle owned by the user.",
                        },
                        "year": {
                            "type": "string",
                            "description": "This is the year of the vehicle owned by the user",
                        },
                    }
                }
            }
        },       
        {
            "type": "function",
            "function": {
                "name": "createSupportRequest",
                "description": """
                Creates a customer support request in the database.
                Useful for when the user wants to create a support request regarding an issue they are facing.
                If you don't have enough information to assist the user or if the user needs actual physical assistance,
                you should create a support request by calling this function.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "This is a title (a brief sentence) summarizing the user's issue. You generate it from the conversation.",
                        },
                        "description": {
                            "type": "string",
                            "description": "A detailed description of the user's issue (under 120 words). You generate it from the user message history. "
                            "It should include the vehicle make, model, year, and issue description EXACTLY as provided by the customer (no added details).",
                        },
                        "model": {
                            "type": "string",
                            "description": "This is the model of the vehicle owned by the user.",
                        },
                        "make": {
                            "type": "string",
                            "description": "This is the make of the vehicle owned by the user.",
                        },
                        "year": {
                            "type": "string",
                            "description": "This is the year of the vehicle owned by the user",
                        },
                    },
                    "required": ["subject", "description", "model", "make", "year"],
                },
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generateImage",
                "description": """
                Calls an image generate model and generates an image according to a text description.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text_prompt": {
                            "type": "string",
                            "description": "A description provided by the user of how the image should look like or what it should contain. "
                            "It can include, objects, environmental elements, background details, etc.",
                        },
                        "size_index": {
                            "type": "integer",
                            "description": "This represents the resolution of the image to be generated. "
                            "The value of this argument needs to be 0, 1 or 2, representing the index of the following resolutions: ['1024x1024', '1792x1024', '1024x1792']",
                        },
                    },
                    "required": ["text_prompt", "size_index"],
                },
            }
        }
    ]

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
## Hybrid Search    --  Chatbot Function
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
## Create Customer Support Request    --  Chatbot Function
####################
def createSupportRequest(user_id, subject, description):
    #This function is used to create a customer support request
    #It stores the request in the database and returns a confirmation message
    
    request_id = SupportDb.addSupportRequest(user_id, subject, description)
    return json.dumps({"request_id": request_id, "status": "Support request created successfully."})

####################
## Validate Support Request    --  Chatbot Function Helper
####################
# def validateSupportRequest(user_messages, parameters_required, arguments):
#     """
#     Validates if a user's message contains the required fields for a support request.
#     checks the values giving to the make, model, and year parameters and uses a regex to 
#     verify that the model didn't hallucinate them.
#     returns an array of the missing/false parameters
#     """
#     missing = []
#     for i in range(len(arguments)):
#         if arguments[i] is None:
#             missing.append(parameters_required[i])
        
#         else:
#             arg = arguments[i].lower()
#             pattern = r'\b' + re.escape(arg) + r'\b'
#             if not re.search(pattern, user_messages):
#                 missing.append(parameters_required[i])
#     return missing

####################
## Generate Image    --  Chatbot Function
####################
def generateImage(user_id, session_id, text_prompt, size_index= 0):
    """
    size_index -> index wrt IMAGE_GEN_SIZES
    Takes a string prompt and a resolution
    Generates an image
    Stores it in the storage blob and and returns an SAS URL
    """
    client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,  
        api_key=AZURE_OPENAI_API_KEY,  
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT
    )

    result = client.images.generate(
        model=AZURE_OPENAI_IMAGE_GEN_DEPLOYMENT_NAME,
        prompt=text_prompt,
        size = IMAGE_GEN_SIZES[size_index],
        n=1,
        response_format="b64_json"
    )

    base64_data = result.data[0].b64_json
    if not base64_data:
        raise ValueError("No base64 image data returned.")

    #uploading image to blob storage
    image_bytes = base64.b64decode(base64_data)
    blob_name = f"{session_id}/{uuid.uuid4()}.png"
    image_sas_url = Container.uploadBlob(container_name=AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME, blob_directory=blob_name, blob_content=image_bytes)

    return image_sas_url