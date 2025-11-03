import azure.functions as func
import azure.identity
import logging
import json
import os

import ChatbotHelpers as ChatbotHelpers
import AISearch
from UsersDb import isAdmin, login
import ChatDb
import CustomerServiceDb as supportDb
import ChatbotMessageHandler as ChatbotMessageHandler
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

############
## User APIs
###########
#
#########   Checks if the user is an admin #################
#
@app.function_name(name="UserIsAdmin")
@app.route(route="user_is_admin", methods=["GET"])
def userIsAdmin(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        is_admin = isAdmin(user_id)
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

@app.function_name(name="UserLogin")
@app.route(route="user_login", methods=["POST"])
def userLogin(req: func.HttpRequest) -> func.HttpResponse:

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

        user = login(email=username, password=password)

        if user:
            return func.HttpResponse(
                json.dumps({"userId": user["userId"], "userType": user["userType"]}),
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
@app.function_name(name="ChatbotSendMessage")
@app.route(route="chatbot_send_message", methods=["POST"])
def chatbotSendMessage(req: func.HttpRequest) -> func.HttpResponse:

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

        reply = ChatbotMessageHandler.sendMessageHelper(user_id, session_id, query)
        
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
@app.function_name(name="ChatbotGetSessions")
@app.route(route="chatbot_get_sessions", methods=["GET"])
def chatbotGetSessions(req: func.HttpRequest) -> func.HttpResponse:

    try:
        user_id = req.params.get("user_id")  

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        sessions = ChatDb.getSessions(user_id)

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
@app.function_name(name="ChatbotCreateSession")
@app.route(route="chatbot_create_session", methods=["POST"])
def chatbotCreateSession(req: func.HttpRequest) -> func.HttpResponse:

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
        
        session_id = ChatbotHelpers.createSession(user_id, session_title)
     
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
@app.function_name(name="ChatbotDeleteSession")
@app.route(route="chatbot_delete_session", methods=["POST"])
def chatbotDeleteSession(req: func.HttpRequest) -> func.HttpResponse:

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
        
        ChatDb.deleteSession(user_id, session_id)

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
@app.function_name(name="ChatbotGetMessagesTrigger")
@app.route(route="chatbot_get_messages", methods=["POST"])
def chatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

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
        
        messages = ChatbotHelpers.listMessages(user_id, session_id)
        
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
@app.function_name(name="ChatbotClearChat")
@app.route(route="chatbot_clear_chat", methods=["POST"])
def chatbotClearChat(req: func.HttpRequest) -> func.HttpResponse:

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
        
        messages = ChatbotHelpers.clearChat(user_id, session_id)

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
#########   Speech To Text #################
#
@app.function_name(name="ChatbotSpeechToText")
@app.route(route="chatbot_speech_to_text", methods=["POST"])
def chatbotSpeechToText(req: func.HttpRequest) -> func.HttpResponse:
    try:
        file = req.files.get("file")
        if not file:
            return func.HttpResponse("No audio file uploaded", status_code=400)

        transcript = ChatbotHelpers.transcribeAudio(file)

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
    
#
#########   Text To Speech #################
#
@app.function_name(name="ChatbotTextToSpeech")
@app.route(route="chatbot_text_to_speech", methods=["POST"])
def chatbotTextToSpeech(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        text = req_body.get("text")

        if not text:
            return func.HttpResponse("Missing 'text' in request body", status_code=400)

        # Get audio bytes (MP3)
        audio_bytes = ChatbotHelpers.generateAudio(text)

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
@app.function_name(name="AISearchListSearchIndexes")
@app.route(route="ai_search_list_indexes", methods=["GET"])
def aiSearchListIndexes(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchListDocuments")
@app.route(route="ai_search_list_documents", methods=["GET"])
def aiSearchListIndexes(req: func.HttpRequest) -> func.HttpResponse:
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
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchGetKeyField")
@app.route(route="ai_search_get_key_field", methods=["GET"])
def aiSearchGetKeyField(req: func.HttpRequest) -> func.HttpResponse:

    try:
        user_id = req.params.get("user_id")
        index_name = req.params.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchCreateIndex")
@app.route(route="ai_search_create_index", methods=["POST"])
def aiSearchCreateIndex(req: func.HttpRequest) -> func.HttpResponse:

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
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchAddDocuments")
@app.route(route="ai_search_add_documents", methods=["POST"])
def aiSearchAddDocuments(req: func.HttpRequest) -> func.HttpResponse:
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
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchDeleteDocument")
@app.route(route="ai_search_delete_document", methods=["POST"])
def aiSearchDeleteDocument(req: func.HttpRequest) -> func.HttpResponse:

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
        
        if not isAdmin(user_id):
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
@app.function_name(name="AISearchDeleteIndex")
@app.route(route="ai_search_delete_index", methods=["POST"])
def aiSearchDeleteIndex(req: func.HttpRequest) -> func.HttpResponse:

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
        
        if not isAdmin(user_id):
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


######################
## Customer Support APIs
#####################
#
#########   List Open Support Requests #################
#
@app.function_name(name="CustomerSupportListOpenRequests")
@app.route(route="customer_support_list_open_requests", methods=["GET"])
def CustomerSupportListOpenRequests(req: func.HttpRequest) -> func.HttpResponse:
    #returns a dic with every retreivable field per doc

    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        requests = supportDb.getOpenSupportRequests()
        
        return func.HttpResponse(
            json.dumps({"open_requests": requests}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in ListOpenRequests HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   List InProgress Support Requests By Agent #################
#
@app.function_name(name="CustomerSupportListInProgressRequestsByAgent")
@app.route(route="customer_support_list_in_progress_requests_by_agent", methods=["GET"])
def CustomerSupportListInProgressRequestsByAgent(req: func.HttpRequest) -> func.HttpResponse:
    #returns a dic with every retreivable field per doc

    try:
        # Parse request body
        user_id = req.params.get("user_id")

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        requests = supportDb.getSupportInProgressRequestsByAgent(user_id)
        
        return func.HttpResponse(
            json.dumps({"in_progress_requests": requests}, ensure_ascii=False).encode('utf-8'),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in ListInProgressRequestsByAgent HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
#
#########  Handle Support Request  #################
#
@app.function_name(name="CustomerSupportHandleSupportRequest")
@app.route(route="customer_support_handle_support_request", methods=["POST"])
def CustomerHandleSupportRequest(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id") #admin id
        request_id = req_body.get("request_id")
        customer_id = req_body.get("customer_id")

        if not user_id or not request_id or not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id, customer_id, and request_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        results = supportDb.handleSupportRequest(user_id, customer_id,request_id)

        if results == -1:
            return func.HttpResponse(
                json.dumps({"error": "This request is already being handled by another agent."}),
                status_code=409,
                mimetype="application/json"
            )
        
        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in HandleSupportRequest HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########  Close Support Request  #################
#
@app.function_name(name="CustomerSupportCloseSupportRequest")
@app.route(route="customer_support_close_support_request", methods=["POST"])
def CustomerCloseSupportRequest(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id") #admin id
        request_id = req_body.get("request_id")
        customer_id = req_body.get("customer_id")

        if not user_id or not request_id or not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id, customer_id, and request_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        supportDb.closeSupportRequest(user_id, customer_id,request_id)

        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in closeSupportRequest HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    

#
#########  Close Support Request  #################
#
@app.function_name(name="CustomerSupportSendEmail")
@app.route(route="customer_support_send_email", methods=["POST"])
def CustomerSendEmail(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id") #admin id
        recipient_id = req_body.get("recipient_id")
        subject = req_body.get("subject")
        body_text = req_body.get("body_text")
        body_html = req_body.get("body_html")

        if  any(param is None for param in [user_id, recipient_id, subject, body_text, body_html]):
            return func.HttpResponse(
                json.dumps({"error": "user_id, recipient_id, subject, body_text, and body_html are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not isAdmin(user_id):
            return func.HttpResponse(
                json.dumps({"error": "This function can only be executed by an admin user"}),
                status_code=400,
                mimetype="application/json"
            )
        
        supportDb.sendEmail(user_id, recipient_id, subject, body_text, body_html)

        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in sendEmail HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )