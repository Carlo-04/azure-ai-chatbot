import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import './App.css'

import Chat from './components/Chat'


function App() {

  return (
    <Router>
      <Routes>
        {/* User Pages */}
        <Route path="/chatbot" element={<Chat />} />
        <Route path="/" element={<Chat/>} />
      </Routes>
    </Router>
  )
}

export default App
