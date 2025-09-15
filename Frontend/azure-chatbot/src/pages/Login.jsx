import { useState, useEffect } from "react";
import axios from "axios";
import { useUser } from "../contexts/UserContext";
import { useNavigate } from "react-router-dom";

export default function Login() {
    const { user, login } = useUser(); 
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();


    const handleSubmit = (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        // try {
        // Replace this URL with your real login API
        // const response = await axios.post("/api/login", { username, password });
        // const user = response.data; 
        // onLogin(user); // Pass user info to parent/context
        // } catch (err) {
        // setError("Invalid username or password");
        // } finally {
        // setLoading(false);
        //  }
        
        //login("c8183593-2547-4289-a752-f3f5e8fb797a", "user");
        login("9c1cd525-31a0-433f-b720-98bfbf12dc1d", "admin");
        navigate("/chatbot");
    }

    return (
        <div className="flex justify-center items-center min-h-screen bg-bg-primary">
        <div className="w-full max-w-md bg-bg-secondary p-8 rounded-lg shadow-md">
            <h2 className="text-2xl text-text-primary font-bold text-center mb-6">Login</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label className="block text-text-secondary mb-1">Username</label>
                <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            <div>
                <label className="block text-text-secondary mb-1">Password</label>
                <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            {error && <p className="text-red-500 text-sm">{error}</p>}

            <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition"
            >
                {loading ? "Logging in..." : "Login"}
            </button>
            </form>
        </div>
        </div>
    );
}
