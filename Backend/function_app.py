import azure.functions as func
import azure.identity
import logging
import json
import os

import Chatbot
import AISearch
import Database

TEST_USER_ID = "16b8fef2-4058-4654-bbba-6bffe2058d28"

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

############
## User APIs
###########
#
#########   Checks if the user is an admin #################
#
@app.function_name(name="IsUserAdmin")
@app.route(route="http_user_is_admin", methods=["GET"])
def httpUserIsAdmin(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        is_admin = Database.isAdmin(user_id)
        return func.HttpResponse(
            json.dumps({"isAdmin": is_admin}),
            status_code=200,
            mimetype="application/json"
        )   
        
    except Exception as e:
        logging.exception("Error in ListSearchIndexes HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="Login")
@app.route(route="http_user_login", methods=["POST"])
def httpUserLogin(req: func.HttpRequest) -> func.HttpResponse:

    try:
        req_body = req.get_json()
    
        username = req_body.get("username")
        password = req_body.get("password")

        if not username or not password:
            return func.HttpResponse(
                json.dumps({"error": "username and password are required"}),
                status_code=400,
                mimetype="application/json"
            )

        user = Database.login(username, password)

        if user:
            return func.HttpResponse(
                json.dumps({"userId": user["userId"], "userType": user["user_type"]}),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "Invalid username or password"}),
                status_code=401,
                mimetype="application/json"
            )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


############
## Chatbot APIs
###########

#
#########   Sending a Message #################
#
@app.function_name(name="MessageTrigger")
@app.route(route="http_chatbot_message", methods=["POST"])
def httpChatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id") 
        session_id = req_body.get("session_id")

        if not session_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )

        query = req_body.get("query")

        reply = Chatbot.sendMessageHelper(user_id, session_id, query)
        
        return func.HttpResponse(
            json.dumps({"reply": reply}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )    

    except Exception as e:
        logging.exception("Error in sendMessage HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   Getting the List of Sessions #################
#
@app.function_name(name="GetSessions")
@app.route(route="http_chatbot_get_sessions", methods=["GET"])
def httpChatbotGetSessions(req: func.HttpRequest) -> func.HttpResponse:

    try:
        user_id = req.params.get("user_id")  

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        sessions = Database.getSessions(user_id)

        #{"session_id": ..., "session_title": ...}
        return func.HttpResponse(
            json.dumps({"sessions": sessions}),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in getting the sessions")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   Creating a Session #################
#
@app.function_name(name="CreateSession")
@app.route(route="http_chatbot_create_session", methods=["POST"])
def httpChatbotCreateSession(req: func.HttpRequest) -> func.HttpResponse:

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")  
        session_title = req_body.get("session_title") 

        if not user_id or not session_title:
            return func.HttpResponse(
                json.dumps({"error": "user_id and a session_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        session_id = Chatbot.createSession(user_id, session_title)
     
        return func.HttpResponse(
            json.dumps({"session_id": session_id, "session_title": session_title}),
            status_code=200,
            mimetype="application/json"
        )

        
    except Exception as e:
        logging.exception("Error in creating a session")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   Deleting a Session #################
#
@app.function_name(name="DeleteSession")
@app.route(route="http_chatbot_delete_session", methods=["POST"])
def httpChatbotDeleteSession(req: func.HttpRequest) -> func.HttpResponse:

    try:
        req_body = req.get_json()
        user_id = req_body.get("user_id")  
        session_id = req_body.get("session_id") 

        if not user_id or not session_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and a session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        Database.deleteSession(user_id, session_id)

        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in deleting the session")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   Getting the List of Messages #################
#
@app.function_name(name="GetMessagesTrigger")
@app.route(route="http_chatbot_get_messages", methods=["POST"])
def httpChatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id")  
        session_id = req_body.get("session_id")

        if not session_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        messages = Chatbot.listMessages(user_id, session_id)
        
        return func.HttpResponse(
            json.dumps({"messages": messages}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in sendMessage HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

#
#########   Clearing Messages #################
#
@app.function_name(name="ClearChatTrigger")
@app.route(route="http_chatbot_clear_chat", methods=["POST"])
def httpChatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id") 
        session_id = req_body.get("session_id")

        if not session_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        messages = Chatbot.clearChat(user_id, session_id)

        return func.HttpResponse(
            json.dumps({"messages": messages}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )      
        

    except Exception as e:
        logging.exception("Error in sendMessage HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    

@app.function_name(name="SpeechToText")
@app.route(route="http_chatbot_speech_to_text", methods=["POST"])
def speechToText(req: func.HttpRequest) -> func.HttpResponse:
    try:
        file = req.files.get("file")
        if not file:
            return func.HttpResponse("No audio file uploaded", status_code=400)

        transcript = Chatbot.transcribeAudio(file)

        return func.HttpResponse(
            body=str(transcript),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error processing speech-to-text: {e}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )
    
@app.function_name(name="TextToSpeech")
@app.route(route="http_chatbot_text_to_speech", methods=["POST"])
def textToSpeech(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        text = req_body.get("text")

        if not text:
            return func.HttpResponse("Missing 'text' in request body", status_code=400)

        # Get audio bytes (MP3)
        audio_bytes = Chatbot.generateAudio(text)

        return func.HttpResponse(
            body=audio_bytes,
            mimetype="audio/mpeg", 
            status_code=200,
            headers={"Content-Disposition": 'inline; filename="speech.mp3"'}
        )

    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)


#################
# AI Search APIs       
###############

#
#########   List Search Indexes #################
#
@app.function_name(name="ListSearchIndexes")
@app.route(route="http_ai_search_list_indexes", methods=["GET"])
def httpAISearchListIndexes(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        indexes = AISearch.listIndexes()
        
        return func.HttpResponse(
            json.dumps({"indexes": indexes}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in ListSearchIndexes HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   List Documents in an Index #################
#
@app.function_name(name="ListDocuments")
@app.route(route="http_ai_search_list_documents", methods=["GET"])
def httpAISearchListIndexes(req: func.HttpRequest) -> func.HttpResponse:
    #returns a dic with every retreivable field per doc

    try:
        # Parse request body
        user_id = req.params.get("user_id")
        index_name = req.params.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        docs = AISearch.listDocuments(index_name)
        
        return func.HttpResponse(
            json.dumps({"documents": docs}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in ListDocuments HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

#
#########   Getting the key field name in an index #################
#
@app.function_name(name="GetKeyField")
@app.route(route="http_ai_search_get_key_field", methods=["GET"])
def httpAISearchGetKeyField(req: func.HttpRequest) -> func.HttpResponse:

    try:
        user_id = req.params.get("user_id")
        index_name = req.params.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        key_field = AISearch.getKeyField(index_name)
        
        return func.HttpResponse(
            json.dumps({"key_field": key_field}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in GetKeyField HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    

#
#########   create search index #################
#
@app.function_name(name="CreateIndex")
@app.route(route="http_ai_search_create_index", methods=["POST"])
def httpAISearchCreateIndex(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        index_name = req_body.get("index_name")


        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id, index_name, and index_fields are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        index_list = AISearch.listIndexes()
        if(index_name in index_list):
            return func.HttpResponse(
                json.dumps({"error": "Index name is already in use"}),
                status_code=409,
                mimetype="application/json"
            )
        
        index_fields = [
            {
                "field_name": "id",
                "field_type": "SimpleField",
                "data_type": "Edm.String",
                "filterable": True
            },
            {
                "field_name": "parent_id",
                "field_type": "SimpleField",
                "data_type": "Edm.String",
                "filterable": True
            },
            {
                "field_name": "chunk_id",
                "field_type": "SimpleField",
                "data_type": "Edm.String",
                "filterable": True,
                "key": True
            },
            {
                "field_name": "chunk_index",
                "field_type": "SimpleField",
                "data_type": "Edm.Int32",
                "sortable": True,
                "filterable": True
            },
            {
                "field_name": "chunk",
                "field_type": "SearchableField",
                "data_type": "Edm.String"
            },
            {
                "field_name": "content_vector",
                "field_type": "SearchField"
            },
            {
                "field_name": "file_name",
                "field_type": "SearchableField",
                "data_type": "Edm.String",
                "filterable": True
            },
            {
                "field_name": "page_number",
                "field_type": "SimpleField",
                "data_type": "Edm.Int32",
                "filterable": True,
                "sortable": True
            }
        ]

        AISearch.createIndex(index_name= index_name, index_fields=index_fields)
        
        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in CreateIndex HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
 
#
#########   add document to an index #################
#
@app.function_name(name="AddDocuments")
@app.route(route="http_ai_search_add_documents", methods=["POST"])
def httpAISearchAddDocuments(req: func.HttpRequest) -> func.HttpResponse:
    #This function receives files, processes them with document intelligence and adds them to the index
    try:
        # Get all uploaded files
        files = req.files #Note: if all files are uplaoded under the same kay, only the first will be read
        index_name = req.form.get("index_name")
        user_id = req.form.get("user_id")

        if not user_id or not index_name:
            return func.HttpResponse("User ID or Index Name is missing", status_code=400)
        
        if not files:
            return func.HttpResponse("No files uploaded", status_code=400)
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )

        uploaded_files = AISearch.addDocumentHelper(index_name=index_name, files=files)

        return func.HttpResponse(
            json.dumps({"uploaded_files": uploaded_files}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error processing upload: {e}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
    
#
#########   delete document from an index #################
#
@app.function_name(name="DeleteDocument")
@app.route(route="http_ai_search_delete_document", methods=["POST"])
def httpAISearchDeleteDocument(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        index_name = req_body.get("index_name")
        file_name = req_body.get("file_name")

        if not user_id or not index_name or not file_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id, index_name, and file_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        AISearch.deleteDocument(index_name= index_name, file_name=file_name)
        
        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in deleteDocument HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

#
#########   delete search index #################
#
@app.function_name(name="DeleteIndex")
@app.route(route="http_ai_search_delete_index", methods=["POST"])
def httpAISearchDeleteIndex(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id")
        index_name = req_body.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not Database.isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        AISearch.deleteIndex(index_name= index_name)
        
        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in deleteIndex HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

