import React, { useState, useEffect } from "react";
import { useLocation, Navigate } from "react-router-dom";
import axios from "axios";
import { jsPDF } from "jspdf";
import { FileUpload } from "primereact/fileupload";
import { ProgressBar } from "primereact/progressbar";
import { useUser } from "../contexts/UserContext";
import LoadingSpinner from "../components/LoadingSpinner";

export default function EditDocuments() {
  const location = useLocation();
  const index_name = location.state?.index_name;
  const { user } = useUser();
  const [documentsList, setDocumentsList] = useState([]); //list of document Names [<string>doc1, <string>doc2]
  const [uploadProgress, setUploadProgress] = useState(null);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsDeleting, setDocumentsDeleting] = useState([]); //this array will hold the indexes of documents being deleted to show loading on their buttons
  if (!index_name) {
    return <Navigate to="admin/knowledge-management" replace />;
  }

  useEffect(() => {
    handleGetDocumentsList();
  }, []);

  const handleGetDocumentsList = async () => {
    try {
      setDocumentsLoading(true);
      const response = await axios.get(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_ai_search_list_documents",
        {
          params: { user_id: user.id, index_name: index_name },
        }
      );

      const documents = response.data.documents;
      setDocumentsList([...new Set(documents.map((doc) => doc.file_name))]);
      setDocumentsLoading(false);
    } catch (error) {
      console.error("Error fetching document list:", error);
    }
  };

  const handleDeleteDocument = async (file_name, index) => {
    try {
      setDocumentsDeleting((prev) => [...prev, index]);
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_ai_search_delete_document",
        {
          user_id: user.id,
          index_name: index_name,
          file_name: file_name,
        }
      );

      setDocumentsDeleting((prev) => prev.filter((i) => i !== index));
      setDocumentsList((prev) => prev.filter((doc) => doc !== file_name));
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
    for (let idx = 0; idx < event.files.length; idx++) {
      let file = event.files[idx];

      // If it's a .txt file, convert to PDF
      if (file.type === "text/plain" || file.name.endsWith(".txt")) {
        const text = await file.text(); // read text
        const doc = new jsPDF();

        // simple: add text (line wrapping handled automatically)
        doc.text(text, 10, 10);

        // create a Blob PDF file
        const pdfBlob = doc.output("blob");
        file = new File([pdfBlob], file.name.replace(/\.txt$/, ".pdf"), {
          type: "application/pdf",
        });
      }

      formData.append(`file${idx}`, file);
    }

    try {
      const response = await axios.post(
        "https://fa-ict-coueiss-sdc-01-d2g5h9gddrcucygu.swedencentral-01.azurewebsites.net/api/http_ai_search_add_documents",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          maxContentLength: Infinity, //actual size restrictions are applied in the FileUpload component
          maxBodyLength: Infinity,
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percent = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              setUploadProgress(percent);
            }
          },
        }
      );
      console.log("Upload response:", response.data);
      if (event.options) {
        event.options.clear(); // clears selected files and resets "pending" status
      }
      setUploadProgress(null);
      handleGetDocumentsList();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed: " + err.message);
      setUploadProgress(null);
    }
  };

  return (
    <div className="px-10 py-5">
      <h1>Search Index Name: {index_name}</h1>
      <div className="flex md:flex-col lg:flex-row mt-10 gap-5">
        {/* Uploading files to the index */}
        <div className="flex flex-1 flex-col w-1/2 justify-content-center">
          {uploadProgress == 100 && (
            <div className="flex flex-row w-full justify-center items-center">
              <div className="w-20 h-20">
                <LoadingSpinner />
              </div>
              Processing Files
            </div>
          )}
          {uploadProgress !== null && (
            <div className="mt-4">
              <ProgressBar value={uploadProgress} showValue />
            </div>
          )}
          <FileUpload
            name="files"
            mode="advanced"
            multiple
            accept="image/*,application/pdf, text/plain"
            maxFileSize={50000000} //50MB
            customUpload
            uploadHandler={customUploader}
            emptyTemplate={
              <p className="m-0 min-h-40">
                Drag and drop files to here to upload.
              </p>
            }
          />
        </div>
        {/* Documents List */}
        <div className="flex flex-1 w-1/2 flex-col gap-2">
          {documentsList.length == 0 && !documentsLoading && (
            <div className="flex w-full h-full rounded-2xl bg-bg-tertiary text-text-secondary items-center justify-center text-lg">
              No Documents Added Yet
            </div>
          )}
          {documentsLoading && (
            <div className="flex w-full h-full rounded-2xl bg-bg-tertiary text-text-secondary items-center justify-center text-lg">
              <div className="flex w-20 h-20 justify-center items-center">
                <LoadingSpinner />
              </div>
            </div>
          )}
          {!documentsLoading &&
            documentsList.map((file_name, idx) => (
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
                    onClick={() => handleDeleteDocument(file_name, idx)}>
                    {documentsDeleting.includes(idx) ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
