import { useState, useEffect, use } from "react";
import axios from "axios";
import "primeicons/primeicons.css";

import LoadingSpinner from "../components/LoadingSpinner";
import { useUser } from "../contexts/UserContext";
import Chat from "../components/Chatbot/Chat";

export default function Chatbot() {
  const [sessionsList, setSessionsList] = useState([]); //[{"session_id": ..., "session_title": ...}]
  const [sessionsListLoading, setSessionsListLoading] = useState(true);
  const [newSessionTitle, setNewSessionTitle] = useState("New Session");
  const [creatingNewSession, setCreatingNewSession] = useState(false); //this is the form to create a new session
  const [newSessionLoading, setNewSessionLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState("");

  const { user } = useUser();

  useEffect(() => {
    handleGetSessionsList();
  }, []);

  const handleGetSessionsList = async () => {
    try {
      const response = await axios.get(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_chatbot_get_sessions",
        {
          params: { user_id: user.id },
        }
      );
      setSessionsListLoading(false);
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
      setNewSessionLoading(true);
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_chatbot_create_session",
        {
          user_id: user.id,
          session_title: newSessionTitle,
        }
      );

      const session = response.data;
      setSessionsList([
        {
          session_id: session.session_id,
          session_title: session.session_title,
        },
        ...sessionsList,
      ]);
      setNewSessionLoading(false);
      setCurrentSessionId(session.session_id);
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
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_chatbot_delete_session",
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
    <div className="flex flex-row justify-start items-center w-full h-full">
      {/* Side bar */}
      <div className=" flex flex-col h-full w-1/5 overflow-auto bg-bg-tertiary">
        {/* Creating Sessions */}
        <div className="flex flex-col w-full items-center py-3">
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
                  {newSessionLoading && "Creating..."}
                  {!newSessionLoading && "Create"}
                </button>
              </div>
            </div>
          )}
          {!creatingNewSession && (
            <button
              className="w-3/4 bg-bg-secondary hover:bg-bg-primary text-txt-primary"
              onClick={() => setCreatingNewSession(true)}>
              New Session
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
                        bg-bg-primary 
                        hover:bg-bg-tertiary">
                    <i className="pi pi-trash"></i>
                  </button>
                </div>
              ))}
          </div>
        )}

        {sessionsList.length == 0 && (
          <div className="flex flex-10 justify-center items-center text-text-secondary">
            {!sessionsListLoading && <p>No Sessions Found</p>}
            {sessionsListLoading && <LoadingSpinner />}
          </div>
        )}
      </div>

      {/* current chat */}
      {currentSessionId != "" && (
        <div className="flex flex-1 w-8/10 h-full p-10 items-start justify-center overflow-auto">
          <div className="flex w-2/3 justify-start items-center">
            <Chat session_id={currentSessionId} />
          </div>
        </div>
      )}
    </div>
  );
}
