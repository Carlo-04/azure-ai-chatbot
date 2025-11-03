import { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./App.css";
import { UserProvider, useUser } from "./contexts/UserContext";

// Pages/Components

// Layout
import Layout from "./components/Layout/Layout";

// User Pages
import Login from "./pages/Login";
import Chatbot from "./pages/Chatbot";

// Admin Pages
import KnowledgeBaseManager from "./pages/Admin/KnowledgeBaseManager";
import EditDocuments from "./pages/Admin/EditDocuments";
import CustomerSupportRequestsPage from "./pages/Admin/CustomerSupportRequestsPage";

// Route Guards
import AdminRoute from "./components/Routes/AdminRoute";
import UserRoute from "./components/Routes/UserRoute";

function App() {
  return (
    <Router>
      <Routes>
        {/* Guest Pages */}
        <Route path="/login" element={<Login />} />

        <Route element={<Layout />}>
          {/* User Pages */}
          <Route element={<UserRoute />}>
            <Route path="/" element={<Chatbot />} />
            <Route path="/chatbot" element={<Chatbot />} />
          </Route>
          {/* Admin Pages */}
          <Route path="/admin" element={<AdminRoute />}>
            <Route
              path="/admin/knowledge-management"
              element={<KnowledgeBaseManager />}
            />
            <Route path="/admin/edit-docs" element={<EditDocuments />} />
            <Route
              path="/admin/customerSupport"
              element={<CustomerSupportRequestsPage />}
            />
          </Route>
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
