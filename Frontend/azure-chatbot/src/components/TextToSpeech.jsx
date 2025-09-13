import React, { useState } from "react";
import axios from "axios";
import 'primeicons/primeicons.css';

export default function TextToSpeech({text}) {
  
    const handleClick = async () => {
        try {
        const response = await axios.post(
            "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_text_to_speech?", 
            { text },
            { responseType: "blob" } 
        );

        // Create a URL for the audio and play it
        const audioUrl = URL.createObjectURL(response.data);
        const audio = new Audio(audioUrl);
        audio.play();
        } catch (error) {
        console.error("Error playing audio:", error);
        }
    };

  return (
    <div>
        <button 
            className="flex items-center justify-center h-1/1 w-3 rounded-full"
            onClick={handleClick}
        >
            <i className='pi pi-volume-up'></i>
        </button>
    </div>
  );
}
