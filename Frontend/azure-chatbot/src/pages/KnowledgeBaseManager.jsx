import React from "react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useUser } from "../contexts/UserContext";
import "primeicons/primeicons.css";

export default function KnowledgeBaseManager() {
  const { user } = useUser();
  const [indexList, setIndexList] = useState([]);
  const [newIndexName, setNewIndexName] = useState("");
  const [isCreatingNewIndex, setIsCreatingNewIndex] = useState(false);
  const navigate = useNavigate();

  const handleCreateIndex = async () => {
    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_create_index?",
        {
          user_id: user.id,
          index_name: newIndexName,
        }
      );

      setIndexList((prevIndexes) => [...prevIndexes, newIndexName]);
      setNewIndexName("");
      setIsCreatingNewIndex(false);
    } catch (error) {
      if (error.response) {
        if (error.response.status === 409) {
          // index name already in use
          alert(
            "This index name is already in use. Please choose a different one."
          );
        }
      } else {
        console.error("Error creating index:", error);
      }
    }
  };

  const handleGetIndexList = async () => {
    try {
      const response = await axios.get(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_list_indexes?",
        {
          params: { user_id: user.id },
        }
      );

      const indexes = response.data.indexes;
      setIndexList(indexes);
    } catch (error) {
      console.error("Error fetching index list:", error);
    }
  };

  const handleDeleteIndex = async (idx) => {
    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_delete_index?",
        {
          user_id: user.id,
          index_name: indexList[idx],
        }
      );

      setIndexList((prevIndexes) => prevIndexes.filter((_, i) => i !== idx));
    } catch (error) {
      console.error("Error fetching deleting index:", error);
    }
  };

  const handleAddDocs = (idx) => {
    navigate("/admin/edit-docs", { state: { index_name: indexList[idx] } });
  };

  useEffect(() => {
    handleGetIndexList();
  }, []);

  return (
    <div className="flex flex-1 flex-col p-4">
      <div>
        <h1>Knowledge Base Manager</h1>
      </div>
      <div className="min-w-100 w-full h-full overflow-y-auto mt-5 space-y-2">
        {indexList.map((item, idx) => (
          <div
            key={idx}
            className="w-full flex items-center justify-between bg-bg-tertiary rounded-md shadow p-3">
            <a
              href="google.com"
              className="text-left font-medium text-text-primary hover:font-bold cursor-pointer">
              {item}
            </a>

            <div className="flex gap-2">
              <button
                className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-primary"
                onClick={() => handleDeleteIndex(idx)}>
                Delete
              </button>
              <button
                className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-primary"
                onClick={() => handleAddDocs(idx)}>
                Edit Documents
              </button>
            </div>
          </div>
        ))}
        {!isCreatingNewIndex && (
          <div className="flex flex-col justify-center items-center content-center">
            <button
              className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-tertiary"
              onClick={() => setIsCreatingNewIndex(true)}>
              Create Index
            </button>
            <p className="text-red-500">
              Note: The chatbot relies on index <i>rag-ict-coueiss-04</i>. I
              will be removing the option to edit indexes
            </p>
          </div>
        )}

        {/* form for creating a new index */}
        {isCreatingNewIndex && (
          <div className="flex flex-col gap-5 mt-5 p-5 items-center">
            <input
              type="text"
              value={newIndexName}
              onChange={(e) => setNewIndexName(e.target.value)}
              placeholder="Search Index Name"
              className="flex p-5 h-3 rounded-md border-1"
            />
            <div className="flex flex-row gap-3 justify-center items-center content-center">
              <button
                className="px-3 py-1 bg-bg-tertiary text-white rounded hover:bg-bg-secondary"
                onClick={() => setIsCreatingNewIndex(false)}>
                Cancel
              </button>
              <button
                className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-tertiary"
                onClick={handleCreateIndex}>
                Confirm
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
