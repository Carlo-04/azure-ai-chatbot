"""
This script includes functions that operform operations on the database realted to chatbot functions.
"""
import uuid
from datetime import datetime, timezone
import os

import Container
from UsersDb import initializeContainer, userIsValid

COSMO_DB_URI = os.getenv("COSMO_DB_URI")
COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")
COSMO_DB_SUPPORT_CONTAINER_NAME = os.getenv("COSMO_DB_SUPPORT_CONTAINER_NAME")

AZURE_COMMUNICATION_ENDPOINT = os.getenv("AZURE_COMMUNICATION_ENDPOINT")
AZURE_COMMUNICATION_API_KEY = os.getenv("AZURE_COMMUNICATION_API_KEY")

AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME")


##################
## Add Message
################
def addMessage(user_id, session_id, message_type, role, content):
    # message_type: "text" or "image"
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    message = {
        "id": str(uuid.uuid4()),  # unique per document
        "userId": user_id,        # partition key
        "sessionId": session_id,
        "documentType": "message",
        "messageType": message_type,
        "role": role,             # "user" or "assistant"
        "content": content,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer(0)
    container.create_item(body=message)

##################
## Add Session
################
def addSession(user_id, session_title):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,  
        "userId": user_id,
        "documentType": "session",
        "sessionTitle": session_title,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer(0)
    container.create_item(body=session)
    return session_id

##################
## Get Sessions
################
def getSessions(user_id):
    # returns a list of dictionaries [{"session_id": ..., "session_title": ...}]

    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    query = """
            SELECT c.sessionTitle, c.id 
            FROM c 
            WHERE c.documentType="session"
            ORDER BY c.createdAt DESC
        """
    
    container = initializeContainer(0)    
    sessions = list(container.query_items(
        query=query,
        partition_key=user_id  
    ))

    formatted_sessions = [
        {"session_id": s["id"], "session_title": s["sessionTitle"]}
        for s in sessions
    ]
    
    return formatted_sessions

##################
## Get Messages
################
def getMessages(user_id, session_id):
    #returns a list of tuples/messages (role, content) for a given session_id

    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    query = """
            SELECT c.role, c.content 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
            ORDER BY c.createdAt ASC
        """
        
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]
    
    container = initializeContainer(0)
    messages = list(container.query_items(
        query=query,
        parameters=parameters,
        partition_key=user_id  #since the partition key is userId, the query will only search within the user's documents
        ))
    return messages

##################
## Delete Session
################
def deleteSession(user_id, session_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    

    # Delete all session's messages from the database
    query_messages = """
            SELECT c.id 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
        """
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]

    container = initializeContainer(0)
    messages = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    
    for message in messages:
        container.delete_item(item=message['id'], partition_key=user_id)
    
    #delete session itself
    container.delete_item(item=session_id, partition_key=user_id)

    #delete all media stored on the storage account (deleting the session directory in the container)
    Container.deleteContainerDirectory(AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME, session_id)

##################
## Clear Session
################
def clearSession(user_id, session_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    # Delete all messages associated with the session
    query_messages = """
            SELECT c.id 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
        """
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]
    container = initializeContainer(0)
    messages = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    
    for message in messages:
        container.delete_item(item=message['id'], partition_key=user_id)

    #delete all media stored on the storage account (deleting the session directory in the container)
    Container.deleteContainerDirectory(AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME, session_id)
