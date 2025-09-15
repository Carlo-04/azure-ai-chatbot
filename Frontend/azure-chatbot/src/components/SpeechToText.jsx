import React, { useState } from "react";
import axios from "axios";
import "primeicons/primeicons.css";

export default function SpeechInput({ onSetInput }) {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Pick the best available audio format
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "audio/wav";

      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        setLoading(true);
        const audio_blob = new Blob(chunks, { type: mimeType });
        const form_data = new FormData();
        form_data.append(
          "file",
          audio_blob,
          `recording.${mimeType.split("/")[1]}`
        );

        try {
          const res = await axios.post(
            "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_speech_to_text?",
            form_data,
            {
              headers: { "Content-Type": "multipart/form-data" },
            }
          );
          onSetInput(res.data);
        } catch (err) {
          console.error("Error sending audio:", err);
          onSetInput("Error transcribing audio.");
        } finally {
          setLoading(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true);
    } catch (err) {
      console.error("Mic access error:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setRecording(false);
    }
  };

  return (
    <div>
      <button
        onClick={recording ? stopRecording : startRecording}
        className={`
              flex items-center justify-center h-1/1 w-3 rounded-full
              ${recording ? "bg-red-400" : "bg-bg-secondary"}
          `}>
        <i className="pi pi-microphone"></i>
      </button>
    </div>
  );
}
