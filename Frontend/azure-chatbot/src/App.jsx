import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import './App.css'
import { UserProvider, useUser } from './contexts/UserContext';
import Chat from './components/Chat'
import KnowledgeBaseManager from './pages/KnowledgeBaseManager';
import EditDocuments from './pages/EditDocuments';
import Login from './pages/Login';
import AdminRoute from './components/AdminRoute';
import UserRoute from './components/UserRoute';

function App() {
  return (
      <Router>
        <Routes>
          {/* Guest Pages */}
          <Route path="/login" element={<Login/>} />

          {/* User Pages */}
          <Route element={<UserRoute />}>
            <Route path="/" element={<Chat />} />
            <Route path="/chatbot" element={<Chat />} />
          </Route>
        
          {/* Admin Pages */}
          <Route path="/admin" element={<AdminRoute />}>
            <Route path="/admin/knowledge-management" element={<KnowledgeBaseManager />} />
            <Route path="/admin/edit-docs" element={<EditDocuments />} />
          </Route>
        </Routes>
      </Router>
  )
}

export default App
