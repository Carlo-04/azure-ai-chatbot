import { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from "react-markdown";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const user_id = "16b8fef2-4058-4654-bbba-6bffe2058d28";
  const session_id = "9669f81b-48ba-42aa-900b-96229e9841d8";


  useEffect(() => {
    
    handleGetMessages();
  }, []); 
    
  const handleGetMessages = async () => {

    const response = await axios.post('https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_get_messages?', {
      "user_id": user_id,
      "session_id": session_id,
    });
    
    const messages_list = response.data.messages;
    setMessages(messages_list.slice(1));
  }

  const handleClearMessages = async () => {
    
    const response = await axios.post('https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_clear_chat?', {
      "user_id": user_id,
      "session_id": session_id,
    });
    
    const messages_list = response.data.messages;
    setMessages(messages_list.slice(1));
  }

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message immediately
    setMessages(prev => [...prev, { 'role': 'user', 'content': input }]);
    const userMessage = input;
    setInput('');

    try { //API call

      const response = await axios.post('https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_message?', {
        "user_id": user_id,
        "session_id": session_id,
        "query": input,
        "rag": true
      });
      
      console.log(response);
      // Add bot response
      setMessages(prev => [...prev, { 'role': 'bot', 'content': response.data.reply }]);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { 'role': 'bot', 'content': '⚠️ Error: could not get response' }]);
    }
  }

  return (
    <div style={{ maxWidth: '800px', margin: 'auto'}}>
      <div
      style={{
        border: "1px solid #ccc",
        borderRadius: "20px",
        padding: "10px",
        minHeight: "300px",
        height: "75%",
        overflowY: "auto",
        backgroundColor: "#111111ff",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {messages.map((msg, index) => (
        <div
          key={index}
          style={{
            textAlign: 'left',
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start", 
            maxWidth: "70%", 
            border: "0px",
            borderRadius: "20px",
            padding: "0px 12px",
            backgroundColor: msg.role === "user" ? "#3f3f3fff" : "#111111ff",
            marginBottom: "5px",
            wordBreak: "break-word", 
          }}
        >
          <ReactMarkdown>{msg.content}</ReactMarkdown>
        </div>
      ))}
    </div>


      <div>
        <div style={{ marginTop: '10px', display: 'flex', gap: '5px' }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type a message..."
            style={{ flex: 1, padding: '5px', height: '30px', borderRadius: '10px', borderWidth: '0px' }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && input != '') {
                e.preventDefault(); // prevent newline in the input
                handleSend();
              }
            }}
          />
        </div>
        <div style={{marginTop: '10px', display: 'flex', gap: '5px'}}>
          <button onClick={handleSend} style = {{width: '50%'}}>Send</button>
          <button onClick={handleClearMessages} style = {{width: '50%'}}>Clear</button>
        </div>
      </div>
    </div>
  );

}
