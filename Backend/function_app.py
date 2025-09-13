import azure.functions as func
import azure.identity
import logging
import json
import os

import Chatbot



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
