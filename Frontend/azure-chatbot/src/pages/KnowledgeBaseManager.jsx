import React from "react";
import { useState, useEffect } from 'react';
import { useNavigate } from "react-router-dom";
import axios from 'axios';
import { useUser } from '../contexts/UserContext';
import 'primeicons/primeicons.css';

export default function KnowledgeBaseManager() {
    const { userId, setUserId } = useUser();
    const [indexList, setIndexList] = useState([]);
    const navigate = useNavigate();

    const handleGetIndexList = async () => {
        try {
            const response = await axios.get(
            "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_list_indexes?",
            {
                params: { user_id: userId }, 
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
            const response = await axios.post('https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_delete_index?', {
                "user_id": userId,
                "index_name": indexList[idx],
                });
            
            setIndexList((prevIndexes) => prevIndexes.filter((_, i) => i !== idx));
        } catch (error) {
            console.error("Error fetching deleting index:", error);
        }
    }

    const handleCreateIndex = () => {
        navigate("/create-index");
    }

    const handleAddDocs = (idx) => {
        navigate("/add-docs", {state: {index_name: indexList[idx]}});
    }
    
    useEffect(() => {
        handleGetIndexList();
    }, []); 

    return(
        <div className="flex flex-1 flex-col justify-start items-center">
            <div>
                <h1>Knowledge Base Manager</h1>
            </div>
            <div className="min-w-100 w-full h-full overflow-y-auto p-4 space-y-2">
                {indexList.map((item, idx) => (
                <div
                    key={idx}
                    className="w-full flex items-center justify-between bg-bg-tertiary rounded-md shadow p-3"
                >
                    <a
                    href="google.com"
                    className="text-left font-medium text-text-primary hover:font-bold cursor-pointer"
                    >
                    {item}
                    </a>
                    
                    <div className="flex gap-2">
                        <button className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-primary"
                            onClick={() => handleDeleteIndex(idx)}>
                        Delete
                        </button>
                        <button className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-primary"
                                onClick={() => handleAddDocs(idx)}>
                            Add Documents
                        </button>
                    </div>
                    
                </div>
                ))}
                <div className="flex justify-center items-center content-center">
                    <button className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-tertiary"
                            onClick={handleCreateIndex}>
                            Create Index
                    </button>
                </div>
            </div>
            
        </div>
    );
}