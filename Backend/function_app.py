import azure.functions as func
import azure.identity
import logging
import json
import os

import Chatbot
import AISearch


TEST_USER_ID = "16b8fef2-4058-4654-bbba-6bffe2058d28"

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

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
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        session_id = req_body.get("session_id")

        if not session_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )

        query = req_body.get("query")
        rag = req_body.get("rag", True)

        reply = Chatbot.sendMessageHelper(user_id, session_id, query, rag)
        
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
#########   Getting the List of Messages #################
#
@app.function_name(name="GetMessagesTrigger")
@app.route(route="http_chatbot_get_messages", methods=["POST"])
def httpChatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
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
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
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
# AI Search APIs        Need to implement checking for admin user
###############

#
#########   List Search Indexes #################
#
@app.function_name(name="ListSearchIndexes")
@app.route(route="http_ai_search_list_indexes", methods=["GET"])
def httpAISearchListIndexes(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        user_id = req.params.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production

        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
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

    try:
        # Parse request body
        user_id = req.params.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req.params.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
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
        user_id = req.params.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req.params.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
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
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req_body.get("index_name")
        index_fields = req_body.get("index_fields")

        if not user_id or not index_name or not index_fields:
            return func.HttpResponse(
                json.dumps({"error": "user_id, index_name, and index_fields are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
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
def httpAISearchCreateIndex(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req_body.get("index_name")
        documents = req_body.get("documents")
        vector_fields = req_body.get(vector_fields)

        if not user_id or not index_name or not documents:
            return func.HttpResponse(
                json.dumps({"error": "user_id, index_name, and documents are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        AISearch.addDocuments(index_name= index_name, documents=documents, vector_fields=vector_fields)
        
        return func.HttpResponse(
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception("Error in AddDocument HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
#
#########   delete document from an index #################
#
@app.function_name(name="DeleteDocument")
@app.route(route="http_ai_search_delete_document", methods=["POST"])
def httpAISearchDeleteDocument(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req_body.get("index_name")
        doc_id = req_body.get("doc_id")

        if not user_id or not index_name or not doc_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id, index_name, and doc_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        AISearch.deleteDocument(index_name= index_name, doc_id=doc_id)
        
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
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        index_name = req_body.get("index_name")

        if not user_id or not index_name:
            return func.HttpResponse(
                json.dumps({"error": "user_id and index_name are required"}),
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




# @app.function_name(name="ProcessDocuments")
# @app.route(route="http_ai_search_process_documents", methods=["POST"])
# def httpAISearchProcessDocuments(req: func.HttpRequest) -> func.HttpResponse:
#     #This function receives files, processes them with document intelligence and adds them to the index
#     try:
#         # Get all uploaded files
#         files = req.files
#         if not files:
#             return func.HttpResponse("No files uploaded", status_code=400)

#         processed_files = []
#         for filename in files:
#             uploaded_file = files[filename]  # type: werkzeug.datastructures.FileStorage
#             content = uploaded_file.read()
            
#             # Here you would feed the file into your document intelligence model
#             # For example: result = process_document(content)
#             processed_files.append({
#                 "filename": uploaded_file.filename,
#                 "size": len(content)
#             })

#         return func.HttpResponse(
#             f"Successfully received {len(processed_files)} files: {processed_files}",
#             status_code=200
#         )

#     except Exception as e:
#         logging.error(f"Error processing upload: {e}")
#         return func.HttpResponse(f"Error: {str(e)}", status_code=500)
    
