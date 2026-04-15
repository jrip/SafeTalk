import { Spin } from "antd";
import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useSafeTalkApi } from "./client/ClientContext";

type TGate = "loading" | "ok" | "denied";

/**
 * Дочерние маршруты доступны только при `role === "admin"`.
 */
export default function RequireAdmin() {
  const api = useSafeTalkApi();
  const [gate, setGate] = useState<TGate>("loading");

  useEffect(() => {
    let cancelled = false;
    void api
      .getCurrentUser()
      .then((u) => {
        if (!cancelled) {
          setGate(u.role === "admin" ? "ok" : "denied");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setGate("denied");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [api]);

  if (gate === "loading") {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }
  if (gate === "denied") {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
