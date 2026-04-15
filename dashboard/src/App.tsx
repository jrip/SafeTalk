import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./auth";
import DashboardLayout from "./layout/DashboardLayout";
import AccountPage from "./pages/AccountPage";
import AdminLedgerPage from "./pages/admin/AdminLedgerPage";
import AdminMlHistoryPage from "./pages/admin/AdminMlHistoryPage";
import AdminStatsPage from "./pages/admin/AdminStatsPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import BalancePage from "./pages/BalancePage";
import HistoryPage from "./pages/HistoryPage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import PredictPage from "./pages/PredictPage";
import RegisterPage from "./pages/RegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import RequireAdmin from "./RequireAdmin";

export interface IProtectedProps {
  readonly children: ReactNode;
}

function Protected(props: IProtectedProps) {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <>{props.children}</>;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route
        element={
          <Protected>
            <DashboardLayout />
          </Protected>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="balance" element={<BalancePage />} />
        <Route path="predict" element={<PredictPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="account" element={<AccountPage />} />
        <Route element={<RequireAdmin />}>
          <Route path="admin/users" element={<AdminUsersPage />} />
          <Route path="admin/stats" element={<AdminStatsPage />} />
          <Route path="admin/ledger" element={<AdminLedgerPage />} />
          <Route path="admin/ml-history" element={<AdminMlHistoryPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
