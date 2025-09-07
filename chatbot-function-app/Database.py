from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

import uuid
from datetime import datetime, timezone
import os

class Database:

    

    __user_id = None #partition key

    def __init__(self, user_id):
        self.__user_id = user_id

        self.COSMO_DB_URI = os.getenv("COSMO_DB_URI")
        self.COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
        self.COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
        self.COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")

        # Initialize Cosmos client only when instance is created
        self.client = CosmosClient(self.COSMO_DB_URI, credential=self.COSMO_DB_PRIMARY_KEY)
        self.database = self.client.get_database_client(self.COSMO_DB_NAME)
        self.container = self.database.get_container_client(self.COSMO_DB_CONVERSATIONS_CONTAINER_NAME)

    @property
    def userId(self):
        return self.__user_id
    
    def isSignedIn(self):
    #function checks if user is signed in or if they're prmopting the chatbot as a guest
        if self.__user_id is None:
            return False
        else:
            return True
    

    def addUser(self, first_name, last_name):
        self.__user_id = str(uuid.uuid4())  
        user = {
            "id": self.__user_id,  # unique per user
            "firstName": first_name,
            "lastName": last_name,
            "documentType": "user",
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        self.container.create_item(body=user)


        
    def addMessage(self, session_id, role, content):
        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to store messages.")
        
        message = {
            "id": str(uuid.uuid4()),  # unique per document
            "userId": self.__user_id,        # partition key
            "sessionId": session_id,
            "documentType": "message",
            "role": role,             # "user" or "assistant"
            "content": content,
            "sentAt": datetime.now(timezone.utc).isoformat()
        }
        self.container.create_item(body=message)

    def addSession(self, session_title):
        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to create a session.")
        
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,  
            "userId": self.__user_id,
            "documentType": "session",
            "sessionTitle": session_title,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        self.container.create_item(body=session)
        return session_id
    
    def getSessions(self):
        #returns a list of tuples/sessions (sessionTitle, sessionId) for the signed-in user

        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to retrieve sessions.")
        
        query = """
                SELECT c.sessionTitle, c.id 
                FROM c 
                WHERE c.documentType="session"
                ORDER BY c.createdAt DESC
            """
            
        sessions = list(self.container.query_items(
            query=query,
            partition_key=self.__user_id  #since the partition key is userId, the query will only search within the user's documents
            ))
        return sessions
    
    def getMessages(self, session_id):
        #returns a list of tuples/messages (role, content) for a given session_id

        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to retrieve messages.")
        
        query = """
                SELECT c.role, c.content 
                FROM c 
                WHERE c.documentType="message" AND c.sessionId=@sessionId
                ORDER BY c.sentAt ASC
            """
            
        parameters = [
            {"name": "@sessionId", "value": session_id}
        ]
        
        messages = list(self.container.query_items(
            query=query,
            parameters=parameters,
            partition_key=self.__user_id  #since the partition key is userId, the query will only search within the user's documents
            ))
        return messages
    
    def deleteSession(self, session_id):
        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to delete a session.")
        
        # Delete all messages associated with the session
        query_messages = """
                SELECT c.id 
                FROM c 
                WHERE c.documentType="message" AND c.sessionId=@sessionId
            """
        parameters = [
            {"name": "@sessionId", "value": session_id}
        ]
        
        messages = list(self.container.query_items(
            query=query_messages,
            parameters=parameters,
            partition_key=self.__user_id
            ))
        
        for message in messages:
            self.container.delete_item(item=message['id'], partition_key=self.__user_id)
        
        # Delete the session itself
        self.container.delete_item(item=session_id, partition_key=self.__user_id)

    def clearSession(self, session_id):
        if not self.isSignedIn():
            raise ValueError("You are not signed in. Please sign in to clear a session.")
        
        # Delete all messages associated with the session
        query_messages = """
                SELECT c.id 
                FROM c 
                WHERE c.documentType="message" AND c.sessionId=@sessionId
            """
        parameters = [
            {"name": "@sessionId", "value": session_id}
        ]
        
        messages = list(self.container.query_items(
            query=query_messages,
            parameters=parameters,
            partition_key=self.__user_id
            ))
        
        for message in messages:
            self.container.delete_item(item=message['id'], partition_key=self.__user_id)

