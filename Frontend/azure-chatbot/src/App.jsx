import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import './App.css'

import Chat from './components/Chat'
import KnowledgeBaseManager from './pages/KnowledgeBaseManager';
import EditDocuments from './pages/EditDocuments';

function App() {

  return (
    <Router>
      <Routes>
        {/* User Pages */}
        <Route path="/chatbot" element={<Chat />} />
        <Route path="/" element={<Chat/>} />
        {/* Admin Pages */}
        <Route path="/knowledge-management" element={<KnowledgeBaseManager />} />
        <Route path="/edit-docs" element={<EditDocuments />} />
      </Routes>
    </Router>
  )
}

export default App
