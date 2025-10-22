import React, { useEffect, useRef, useState } from "react";
import { useUser } from "../../contexts/UserContext";

const SpeechToSpeech = () => {
  const wsRef = useRef(null);
  const sourceNodesRef = useRef([]);
  const audioCtxRef = useRef(null);
  const nextStartTimeRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const [currentMsgTranscript, setCurrentMsgTranscript] = useState("");

  const currentResponseIdRef = useRef("");
  const { user } = useUser();

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/realtime");
    ws.binaryType = "arraybuffer";

    const audioContext = new (window.AudioContext || window.webkitAudioContext)(
      {
        sampleRate: 24000,
      }
    );

    ws.onopen = () => {
      console.log("Connected to WebSocket server");
      ws.send(user.id);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      const data = event.data;
      if (typeof data !== "string") {
        playPCMChunk(data);
      } else {
        // If String
        if (data == "ready") {
          setIsConnected(true);
        } else if (data == "function_in_progress") {
          setCurrentMsgTranscript("Processing your request...");
        }
        // If Json
        if (isJSON(data)) {
          const data_json = JSON.parse(data);
          if (data_json.response_id === currentResponseIdRef.current) {
            setCurrentMsgTranscript(
              (prev) => prev + data_json.transcript_delta
            );
          } else {
            currentResponseIdRef.current = data_json.response_id;
            setCurrentMsgTranscript(data_json.transcript_delta);

            clearAudioBuffer(); //stop any enqueued audio chunks
          }
        }
      }
    };

    wsRef.current = ws;
    audioCtxRef.current = audioContext;

    return () => {
      ws.close();
      audioContext.close();
    };
  }, []);

  //////////////////////
  // AUDIO PLAYBACK
  //////////////////////
  const playPCMChunk = (arrayBuffer) => {
    const audioCtx = audioCtxRef.current;
    const int16Data = new Int16Array(arrayBuffer);
    const floatData = new Float32Array(int16Data.length);

    // Convert PCM16 → Float32
    for (let i = 0; i < int16Data.length; i++) {
      floatData[i] = int16Data[i] / 32768;
    }

    const audioBuffer = audioCtx.createBuffer(1, floatData.length, 24000);
    audioBuffer.copyToChannel(floatData, 0);

    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);

    const startTime = Math.max(audioCtx.currentTime, nextStartTimeRef.current);
    source.start(startTime);
    nextStartTimeRef.current = startTime + audioBuffer.duration;

    // Keep track of the node so we can cancel it later
    sourceNodesRef.current.push(source);
    // Optional: remove it after it finishes playing
    // source.onended = () => {
    //   sourceNodesRef.current = sourceNodesRef.current.filter(
    //     (s) => s !== source
    //   );
    // };
  };

  // Function to stop all queued audio
  const clearAudioBuffer = () => {
    sourceNodesRef.current.forEach((source) => {
      try {
        source.stop(); // stops both playing and scheduled nodes
      } catch (e) {
        // may throw if node already stopped
      }
    });
    sourceNodesRef.current = [];
    nextStartTimeRef.current = audioCtxRef.current.currentTime;
  };

  //////////////////////
  // AUDIO RECORDING (PCM16 streaming)
  //////////////////////

  const startRecording = async () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error("❌ WebSocket is not open.");
      return;
    }

    // Ask for mic access
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioCtxRef.current = new (window.AudioContext ||
      window.webkitAudioContext)({
      sampleRate: 24000, // Match backend sample rate if possible
    });

    const audioCtx = audioCtxRef.current;
    sourceRef.current = audioCtx.createMediaStreamSource(stream);

    // Create a ScriptProcessorNode to process raw PCM samples
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const pcm16 = floatTo16BitPCM(input);

      // Send raw binary directly
      ws.send(pcm16.buffer);
    };

    sourceRef.current.connect(processor);
    processor.connect(audioCtx.destination);

    setIsRecording(true);
    console.log("🎙️ Recording started...");
  };

  const stopRecording = () => {
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    setIsRecording(false);
    console.log("🛑 Recording stopped.");
  };

  // Convert Float32Array [-1.0, 1.0] → Int16Array PCM16
  const floatTo16BitPCM = (float32Array) => {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return new Int16Array(buffer);
  };

  // Encode binary data to Base64
  const arrayBufferToBase64 = (buffer) => {
    let binary = "";
    const bytes = new Uint8Array(buffer);
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, chunk);
    }
    return btoa(binary);
  };

  /////////////
  // Helpers
  ///////////
  function isJSON(str) {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  }

  return (
    <div className="p-4 flex flex-col gap-5 justify-center items-center w-full h-full">
      <div className="flex w-3/4 h-1/2 max-h-3/4 max-w-3/4 justify-center items-center text-center text-text-primary bg-bg-tertiary rounded-2xl p-2">
        {currentMsgTranscript}
      </div>
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={!isConnected}
        className={`px-6 py-3 rounded-lg text-white ${
          isRecording
            ? "bg-red-500"
            : isConnected
            ? "bg-green-500"
            : "bg-gray-400"
        }`}>
        {isRecording ? "Pause" : isConnected ? "Start" : "Connecting..."}
      </button>
      <p>Pause button still needs debugging. Don't pause mid-conversation.</p>
    </div>
  );
};

export default SpeechToSpeech;
