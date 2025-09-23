import { Navigate, Outlet, useNavigate } from "react-router-dom";
import { useUser } from "../../contexts/UserContext";

export default function UserRoute() {
  const { user } = useUser();

  const navigate = useNavigate();

  return user.id ? <Outlet /> : <Navigate to="/login" replace />;
}
