import React, { useState } from "react";
import { Sidebar } from "primereact/sidebar";
import { Link } from "react-router-dom";
import { Button } from "primereact/button";
import "primeicons/primeicons.css";

import { useUser } from "../../contexts/UserContext";

export default function SideBar() {
  const [visible, setVisible] = useState(false);
  const { user } = useUser();

  return (
    <div className="card flex justify-content-center">
      <Sidebar visible={visible} onHide={() => setVisible(false)}>
        <div className="flex flex-col h-full">
          {/* User Pages*/}
          <div className="flex flex-1 flex-col">
            <p className="font-bold text-2xl shadow-2xl">User Pages</p>
            <nav className="flex flex-col text-lg">
              <Link
                to="/chatbot"
                className="hover:font-medium w-full"
                onClick={() => setVisible(false)}>
                Chatbot
              </Link>
            </nav>
          </div>

          {/* Admin Pages*/}
          {user.type === "admin" && (
            <div className="flex flex-1 flex-col">
              <p className="font-bold text-2xl shadow-2xl">Admin Pages</p>
              <nav className="flex flex-col">
                <Link
                  to="/admin/knowledge-management"
                  className="hover:font-medium w-full text-lg"
                  onClick={() => setVisible(false)}>
                  Knowledge Base
                </Link>
              </nav>
            </div>
          )}
        </div>
      </Sidebar>
      <button
        className="flex 
					items-center 
					justify-center 
					h-1/1 w-10 
					rounded-full 
					bg-transparent"
        onClick={() => setVisible(true)}>
        <i className="pi pi-bars" style={{ fontSize: "1.7rem" }}></i>
      </button>
    </div>
  );
}
