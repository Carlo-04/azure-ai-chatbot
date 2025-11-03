import React from "react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useUser } from "../../contexts/UserContext";
import "primeicons/primeicons.css";

export default function KnowledgeBaseManager() {
  const { user } = useUser();
  const [indexList, setIndexList] = useState([]);
  const [newIndexName, setNewIndexName] = useState("");
  const [isCreatingNewIndex, setIsCreatingNewIndex] = useState(false);
  const [currentIndexName, setCurrentIndexName] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    handleGetIndexList();
    handleGetIndexName();
  }, []);

  /////////
  // API Calls
  /////////

  const handleGetIndexName = async () => {
    try {
      const response = await axios.get(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/ai_search_get_index_name",
        {
          params: { user_id: user.id },
        }
      );
      const index_name = response.data.index_name;
      setCurrentIndexName(index_name);
    } catch (error) {
      console.error("Error fetching current index name:", error);
    }
  };
  const handleCreateIndex = async () => {
    try {
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/ai_search_create_index",
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
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/ai_search_list_indexes",
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
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/ai_search_delete_index",
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
            <p
              className="text-left font-medium text-text-primary hover:font-bold cursor-pointer"
              onClick={() => handleAddDocs(idx)}>
              {item}
            </p>

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

            <p className="text-text-secondary text-center">
              Search Index In Use: <b>{currentIndexName}</b>
              <br />
              To change it, you must modify the app's environment variables.
            </p>
          </div>
        )}

        {/* form for creating a new index */}
        {isCreatingNewIndex && (
          <div className="flex flex-col gap-5 mt-5 p-5 items-center text-text-primary">
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
