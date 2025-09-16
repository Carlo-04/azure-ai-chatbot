import { useState, useEffect, use } from "react";
import axios from "axios";
import "primeicons/primeicons.css";

import { useUser } from "../contexts/UserContext";
import Chat from "../components/Chat";

export default function Chatbot() {
  const [sessionsList, setSessionsList] = useState([]); //[{"session_id": ..., "session_title": ...}]
  const [newSessionTitle, setNewSessionTitle] = useState("New Session");
  const [creatingNewSession, setCreatingNewSession] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const { user } = useUser();

  useEffect(() => {
    handleGetSessionsList();
  }, []);

  const handleGetSessionsList = async () => {
    try {
      const response = await axios.get(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_get_sessions?",
        {
          params: { user_id: user.id },
        }
      );
      setSessionsList(response.data.sessions);
    } catch (error) {
      console.error(
        "Error fetching sessions:",
        error.response?.data || error.message
      );
    }
  };

  const handleCreateSession = async () => {
    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_create_session?",
        {
          user_id: user.id,
          session_title: newSessionTitle,
        }
      );

      const session = response.data;
      setSessionsList([
        ...sessionsList,
        {
          session_id: session.session_id,
          session_title: session.session_title,
        },
      ]);
      setNewSessionTitle("New Session");
      setCreatingNewSession(false);
    } catch (error) {
      console.error(
        "Error creating session:",
        error.response?.data || error.message
      );
    }
  };

  const handleDeleteSession = async (target_session_id) => {
    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_chatbot_delete_session?",
        {
          user_id: user.id,
          session_id: target_session_id,
        }
      );

      setSessionsList((prevList) =>
        prevList.filter((session) => session.session_id !== target_session_id)
      );
      if (currentSessionId == target_session_id) {
        setCurrentSessionId("");
      }
    } catch (error) {
      console.error(
        "Error deleting session:",
        error.response?.data || error.message
      );
    }
  };
  return (
    <div className="flex flex-row justify-start items-center fixed inset-0">
      {/* Side bar */}
      <div className=" flex flex-col h-full w-1/5 overflow-auto border-r-[0.5px] bg-bg-tertiary">
        {/* Creating Sessions */}
        <div className="flex flex-1 flex-col w-full items-center py-3">
          {creatingNewSession && (
            <div>
              <label className="block text-text-secondary mb-1">
                New Session Title
              </label>
              <input
                type="text"
                value={newSessionTitle}
                onChange={(e) => setNewSessionTitle(e.target.value)}
                required
                className="w-full px-4 py-2 border-[0.5px] border-text-secondary rounded-md"
              />
              <div className="flex flex-row justify-center gap-2 my-3">
                <button
                  className="w-1/2 bg-bg-primary hover:bg-bg-tertiary text-txt-primary"
                  onClick={() => setCreatingNewSession(false)}>
                  Cancel
                </button>
                <button
                  className="w-1/2 bg-bg-secondary hover:bg-bg-tertiary text-txt-primary"
                  onClick={handleCreateSession}>
                  Create
                </button>
              </div>
            </div>
          )}
          {!creatingNewSession && (
            <button
              className="w-3/4 bg-bg-secondary hover:bg-bg-primary text-txt-primary"
              onClick={() => setCreatingNewSession(true)}>
              Create index
            </button>
          )}
        </div>
        {/* Sessions List */}
        {sessionsList.length > 0 && (
          <div className="flex flex-10 flex-col justify-start items-center text-text-secondary">
            {sessionsList.length > 0 &&
              sessionsList.map((session, idx) => (
                <div
                  key={idx}
                  className={`
                    w-full flex items-center justify-between hover:bg-bg-secondary  rounded-md shadow p-3
                    ${
                      session.session_id === currentSessionId
                        ? "bg-bg-secondary"
                        : "bg-inherit"
                    }
                    `}>
                  <div
                    className="cursor-pointer hover:font-semibold"
                    onClick={() => setCurrentSessionId(session.session_id)}>
                    {session.session_title}
                  </div>
                  <button
                    onClick={() => handleDeleteSession(session.session_id)}
                    className="flex 
                        items-center 
                        justify-center 
                        h-1/1 w-3 
                        rounded-full 
                        bg-bg-primary">
                    <i className="pi pi-trash"></i>
                  </button>
                </div>
              ))}
          </div>
        )}

        {sessionsList.length == 0 && (
          <div className="flex flex-10 justify-center items-center text-text-secondary">
            No Sessions Found
          </div>
        )}
      </div>

      {/* current chat */}
      {currentSessionId != "" && (
        <div className="flex w-8/10 px-10 items-center justify-center overflow-auto">
          <div className="w-2/3">
            <Chat session_id={currentSessionId} />
          </div>
        </div>
      )}
    </div>
  );
}
