import { Navigate, Outlet, useNavigate } from "react-router-dom";
import { useUser } from "../../contexts/UserContext";

export default function AdminRoute() {
  const { user } = useUser();
  const navigate = useNavigate();

  if (!user.id) navigate("/login");

  // Only allow admins
  return user.type === "admin" ? <Outlet /> : <Navigate to="/" replace />;
}
