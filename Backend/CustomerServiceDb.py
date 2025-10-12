"""
This script includes functions to perform operations related to customer service request in their respective container in the database.
Operations also include any communication features used to communicate with the user while handling requests.
"""

from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential

import uuid
from datetime import datetime, timezone
import os

from UsersDb import initializeContainer, userIsValid, getUserInfo

COSMO_DB_URI = os.getenv("COSMO_DB_URI")
COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")
COSMO_DB_SUPPORT_CONTAINER_NAME = os.getenv("COSMO_DB_SUPPORT_CONTAINER_NAME")

AZURE_COMMUNICATION_ENDPOINT = os.getenv("AZURE_COMMUNICATION_ENDPOINT")
AZURE_COMMUNICATION_API_KEY = os.getenv("AZURE_COMMUNICATION_API_KEY")

AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_IMAGES_CONTAINER_NAME")


#############
## Get Open Support Requests
#############
def getOpenSupportRequests():
    query = """
            SELECT c.id, c.userId, c.subject, c.description, c.createdAt
            FROM c 
            WHERE c.documentType="support_request" AND c.status="open"
            ORDER BY c.createdAt ASC
        """
    
    container = initializeContainer(1)    
    requests = list(container.query_items(
        query=query,
        partition_key="none"
    ))

    formatted_requests = [
        {
            "request_id": r["id"], 
            "user_id": r["userId"], 
            "subject": r["subject"], 
            "description": r["description"], 
            "createdAt": r["createdAt"]
        }
        for r in requests
    ]
    
    return formatted_requests

#############
## Get support requests that are in progress and assigned to a certain agent
#############
def getSupportInProgressRequestsByAgent(user_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)    
    query = """
            SELECT c.id, c.userId, c.subject, c.description, c.status, c.createdAt
            FROM c 
            WHERE c.documentType="support_request" AND c.supportAgentId=@userId AND c.status = "in_progress"
            ORDER BY c.createdAt ASC
        """
    parameters = [
        {"name": "@userId", "value": user_id}
    ]
    
    requests = list(container.query_items(
        query=query,
        parameters=parameters,
        partition_key=user_id
    ))

    formatted_requests = [
        {
            "request_id": r["id"], 
            "user_id": r["userId"], 
            "subject": r["subject"], 
            "description": r["description"], 
            "status": r["status"],
            "createdAt": r["createdAt"]
        }
        for r in requests
    ]
    
    return formatted_requests

#############
## Add Support Request
#############
def addSupportRequest(user_id, subject, description):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    request_id = str(uuid.uuid4())
    support_request = {
        "id": request_id,  
        "userId": user_id,
        "documentType": "support_request",
        "subject": subject,
        "description": description,
        "status": "open",  # open, in_progress, resolved
        "supportAgentId": "none",  # to be assigned later
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer(1)
    container.create_item(body=support_request)
    return request_id

#############
## Handle/Assign Suppport Request
#############
def handleSupportRequest(user_id, customer_id, request_id):
    # This function assigns a support request to an agent (user_id) once the agent selects it
    if not userIsValid(user_id) or not userIsValid(customer_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)

    query_messages = """
            SELECT *
            FROM c 
            WHERE c.documentType="support_request" AND c.id=@id
        """
    parameters = [
        {"name": "@id", "value": request_id}
    ]
    requests = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key="none"
        ))
    if requests:
        request = requests[0]
        if request["supportAgentId"] != "none":
            return -1  # already assigned to another agent
        
        container.delete_item(
            item=request["id"],
            partition_key="none"
        )
        
        request["status"] = 'in_progress'
        request["supportAgentId"] = user_id
        container.create_item(body=request)
    else:
        raise ValueError("This request does not exist anymore.")


#############
## Close/Resolve Support Request
#############
def closeSupportRequest(user_id, customer_id, request_id):
    # This function closes a support request and markes it as resolved
    if not userIsValid(user_id) or not userIsValid(customer_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)

    query_messages = """
            SELECT *
            FROM c 
            WHERE c.documentType="support_request" AND c.id=@id
        """
    parameters = [
        {"name": "@id", "value": request_id}
    ]
    requests = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    if requests:
        request = requests[0]
        if request["supportAgentId"] != user_id:
            raise ValueError("This request is assigned to another agent.")
        
        request["status"] = 'resolved'
        container.replace_item(item=request["id"], body=request)
    else:
        raise ValueError("This request does not exist anymore.")
    

#############
## Send Email
#############
def sendEmail(user_id, recipient_id, subject, body_text, body_html):
    if not userIsValid(user_id) or not userIsValid(recipient_id):
        raise ValueError("This user does not exist")
    
    sender_email = "DoNotReply@a4a02730-2bef-46ed-beaa-64e5c3ed0fc9.azurecomm.net"
    recipient_info = getUserInfo(recipient_id)
    rec_email = recipient_info.get("email")
    rec_fname = recipient_info.get("firstName")
    rec_lname = recipient_info.get("lastName")
    email_client = EmailClient(endpoint=AZURE_COMMUNICATION_ENDPOINT, credential=AzureKeyCredential(AZURE_COMMUNICATION_API_KEY))

    message = {
        "content": {
            "subject": subject,
            "plainText": body_text,
            "html": body_html
        },
        "recipients": {
            "to": [
                {
                    "address": rec_email,
                    "displayName": f"{rec_fname} {rec_lname}"
                }
            ]
        },
        "senderAddress": sender_email
    }   
    poller = email_client.begin_send(message)
    return poller.result()