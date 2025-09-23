import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "primereact/button";
import { useUser } from "../../contexts/UserContext";
import { Navigate, useNavigate } from "react-router-dom";
import SideBar from "./SideBar";

export default function TopBar() {
  const { user, logout } = useUser();

  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="w-full bg-bg-secondary text-text-primary shadow-md px-6 py-3 flex items-center justify-between">
      <SideBar />

      <div className="flex items-center justify-center gap-5">
        <button
          className="p-button-rounded p-button-outlined p-button-sm bg-bg-tertiary"
          onClick={handleLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}
