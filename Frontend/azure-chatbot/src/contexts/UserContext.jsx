import React, { createContext, useContext, useState, useEffect } from "react";

// Create the context
const UserContext = createContext();

// Create the provider component
export const UserProvider = ({ children }) => {

  const [user, setUser] = useState(() => {
    const storedUser = localStorage.getItem("user");
    return storedUser ? JSON.parse(storedUser) : { id: null, type: null };
  });


  const login = (id, type) => {
    const newUser = { id, type };
    setUser(newUser);
    localStorage.setItem("user", JSON.stringify(newUser));
  };


  const logout = () => {
    setUser({ id: null, type: null });
    localStorage.removeItem("user");
  };


  return (
    <UserContext.Provider value={{ user, login, logout }}>
      {children}
    </UserContext.Provider>
  );
};

// Custom hook for easy access
export const useUser = () => useContext(UserContext);
