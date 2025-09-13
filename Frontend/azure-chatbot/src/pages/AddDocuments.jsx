import React from "react";
import { useState, useEffect } from 'react';
import { useLocation, Navigate } from "react-router-dom";
import axios from 'axios';
import { FileUpload } from 'primereact/fileupload';

export default function AddDocuments() {
    const location = useLocation();
    const index_name = location.state?.index_name;

    if(!index_name){
        return <Navigate to="/knowledge-management" replace />
    }

    const handleUpload = (event) => {
        // event.xhr contains the raw XMLHttpRequest
        // event.files contains the uploaded files
        const responseText = event.xhr.responseText; // raw response
        try {
            const responseJson = JSON.parse(responseText); // parse if your backend returns JSON
            console.log('Upload response:', responseJson);
        } catch (err) {
            console.log('Upload response (raw):', responseText);
        }
    };

    const handleError = (event) => {
        console.error('Upload error:', event);
    };

    

    return (
        <div className="flex content-center items-center">
            <FileUpload name="files[]"
            url={'http://localhost:7071/api/http_ai_search_process_documents'} 
            multiple accept="image/*,application/pdf,text/plain"
            maxFileSize={1000000} 
            emptyTemplate={<p className="m-0">Drag and drop files to here to upload.</p>}
            onUpload={handleUpload}
            onError={handleError} 
            />
            
        </div>
  );
}