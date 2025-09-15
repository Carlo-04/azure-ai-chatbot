import { useState, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import SpeechInput from "./SpeechToText";
import TextToSpeech from "./TextToSpeech";
import { useUser } from "../contexts/UserContext";
import "primeicons/primeicons.css";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const { user } = useUser();

  const session_id = "9669f81b-48ba-42aa-900b-96229e9841d8";

  useEffect(() => {
    console.log(user.id);
    handleGetMessages();
  }, []);

  const handleSetInput = (text) => {
    setInput((prevInput) => prevInput + " " + text);
  };

  const handleGetMessages = async () => {
    const response = await axios.post(
      "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_get_messages?",
      {
        user_id: user.id,
        session_id: session_id,
      }
    );

    const messages_list = response.data.messages;
    setMessages(messages_list.slice(1));
  };

  const handleClearMessages = async () => {
    const response = await axios.post(
      "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_clear_chat?",
      {
        user_id: user.id,
        session_id: session_id,
      }
    );

    const messages_list = response.data.messages;
    setMessages(messages_list.slice(1));
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message immediately
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    const userMessage = input;
    setInput("");

    try {
      //API call

      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_message?",
        {
          user_id: user.id,
          session_id: session_id,
          query: input,
          rag: true,
        }
      );

      console.log(response);
      // Add bot response
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: response.data.reply },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: "⚠️ Error: could not get response" },
      ]);
    }
  };

  return (
    <div className="max-w-3/4 m-auto">
      <div
        className="
        border border-gray-300      
        rounded-2xl             
        p-2.5                     
        min-h-75         
        h-3/4               
        overflow-y-auto         
        bg-bg-tertiary         
        flex flex-col             
      ">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex items-center ${
              msg.role === "user" ? "justify-end" : "justify-start"
            } mb-2`}>
            <div
              key={index}
              className={`
              text-left
              ${
                msg.role === "user"
                  ? "self-end bg-bg-tertiary"
                  : "self-start bg-bg-secondary"
              }
              max-w-3/4
              rounded-2xl
              px-3 py-2
              mb-2
              break-words
            `}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>

            {msg.role === "assistant" && (
              <div
                className="flex 
                items-center 
                justify-center 
                h-10 w-10 
                rounded-full
                ml-2 
                bg-bg-secondary">
                <TextToSpeech text={msg.content} />
              </div>
            )}
          </div>
        ))}
      </div>

      <div>
        <div className="flex flex-row mt-10 gap-5 items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex flex-1 p-5 h-3 rounded-md border-1"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && input != "") {
                e.preventDefault(); // prevent newline in the input
                handleSend();
              }
            }}
          />
          <div className="flex flex-row gap-2">
            <button
              onClick={handleClearMessages}
              className="flex 
                items-center 
                justify-center 
                h-1/1 w-3 
                rounded-full 
                bg-bg-secondary">
              <i className="pi pi-times"></i>
            </button>
            <SpeechInput onSetInput={handleSetInput} />
            <button
              onClick={handleSend}
              className="flex 
                items-center 
                justify-center 
                h-1/1 w-3 
                rounded-full 
                bg-bg-secondary">
              <i className="pi pi-send"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
