import React, { useState, useEffect } from "react";
import { useLocation, Navigate } from "react-router-dom";
import { FileUpload } from "primereact/fileupload";
import { useUser } from "../contexts/UserContext";
import axios from "axios";

export default function EditDocuments() {
  const location = useLocation();
  const index_name = location.state?.index_name;
  const { user } = useUser();
  const [documentsList, setDocumentsList] = useState([]); //list of document Names [<string>doc1, <string>doc2]

  if (!index_name) {
    return <Navigate to="admin/knowledge-management" replace />;
  }

  useEffect(() => {
    handleGetDocumentsList();
  }, []);

  const handleGetDocumentsList = async () => {
    try {
      const response = await axios.get(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_list_documents?",
        {
          params: { user_id: user.id, index_name: index_name },
        }
      );

      const documents = response.data.documents;
      setDocumentsList([...new Set(documents.map((doc) => doc.file_name))]);
    } catch (error) {
      console.error("Error fetching document list:", error);
    }
  };

  const handleDeleteDocument = async (file_name) => {
    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_delete_document?",
        {
          user_id: user.id,
          index_name: index_name,
          file_name: file_name,
        }
      );

      if (response.status === 200) {
        handleGetDocumentsList();
      }
    } catch (error) {
      if (error.response) {
        console.error("Error:", error.response.data);
      } else {
        // Network or other error
        console.error("Request failed:", error.message);
        alert("Request failed. Please try again.");
      }
    }
  };

  const customUploader = async (event) => {
    if (!event.files || event.files.length === 0) return;

    const formData = new FormData();
    formData.append("index_name", index_name);
    formData.append("user_id", user.id);
    // append all selected files with unique keys
    event.files.forEach((file, idx) => {
      formData.append(`file${idx}`, file);
    });

    try {
      const response = await axios.post(
        "https://fa-ict-oueiss-sdc-01-dydvgchzadehataz.swedencentral-01.azurewebsites.net/api/http_ai_search_add_documents?",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      console.log("Upload response:", response.data);
      if (event.options) {
        event.options.clear(); // clears selected files and resets "pending" status
      }

      alert("Files uploaded successfully!");
      handleGetDocumentsList();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed: " + err.message);
    }
  };

  return (
    <div>
      <h1>Search Index Name: {index_name}</h1>
      <div className="flex flex-row w-screen mt-10">
        <div className="flex w-1/2 flex-col gap-2">
          {documentsList.length == 0 && (
            <div className="flex w-full h-full rounded-2xl bg-bg-tertiary text-text-secondary items-center justify-center text-lg">
              No Documents Added Yet
            </div>
          )}
          {documentsList.map((file_name, idx) => (
            <div
              key={idx}
              className="w-full flex items-center justify-between bg-bg-tertiary rounded-md shadow p-3">
              <a
                href="google.com"
                className="text-left font-medium text-text-primary hover:font-bold cursor-pointer">
                {file_name}
              </a>

              <div className="flex gap-2">
                <button
                  className="px-3 py-1 bg-bg-secondary text-white rounded hover:bg-bg-primary"
                  onClick={() => handleDeleteDocument(file_name)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
        <div className="card flex w-1/2 justify-content-center">
          <FileUpload
            name="files"
            mode="advanced"
            multiple
            accept="image/*,application/pdf"
            maxFileSize={100000000} //100MB
            customUpload
            uploadHandler={customUploader}
            emptyTemplate={
              <p className="m-0">Drag and drop files to here to upload.</p>
            }
          />
        </div>
      </div>
    </div>
  );
}
