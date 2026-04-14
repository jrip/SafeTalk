import {
  ApiOutlined,
  BarChartOutlined,
  HistoryOutlined,
  HomeOutlined,
  LogoutOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  TransactionOutlined,
  UserOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import type { MenuProps } from "antd";
import { Button, Layout, Menu, Tag, Typography } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearToken } from "../auth";
import type { IUserProfile } from "../client/contracts";
import { useSafeTalkApi } from "../client/ClientContext";

const { Header, Sider, Content } = Layout;

/** Одна линия с нижней границей: логотип слева и шапка справа. */
const DASHBOARD_TOPBAR_HEIGHT = 64;

export default function DashboardLayout() {
  const location = useLocation();
  const nav = useNavigate();
  const api = useSafeTalkApi();
  const [me, setMe] = useState<IUserProfile | null | undefined>(undefined);

  const loadMe = useCallback(() => {
    void api
      .getCurrentUser()
      .then(setMe)
      .catch(() => setMe(null));
  }, [api]);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  const isAdmin = me != null && me.role === "admin";

  const selectedKey = useMemo(() => {
    const p = location.pathname;
    if (p === "/" || p === "") {
      return "/";
    }
    return p;
  }, [location.pathname]);

  const menuItems: MenuProps["items"] = useMemo(() => {
    const base: MenuProps["items"] = [
      { key: "/", icon: <HomeOutlined />, label: <Link to="/">Обзор</Link> },
      { key: "/account", icon: <UserOutlined />, label: <Link to="/account">Профиль</Link> },
      { key: "/balance", icon: <WalletOutlined />, label: <Link to="/balance">Баланс</Link> },
      { key: "/predict", icon: <ThunderboltOutlined />, label: <Link to="/predict">Запрос</Link> },
      { key: "/history", icon: <HistoryOutlined />, label: <Link to="/history">История</Link> },
      {
        key: "docs-public",
        icon: <ApiOutlined />,
        label: (
          <a href="/docs-public" target="_blank" rel="noopener noreferrer">
            Публичное API (Swagger)
          </a>
        ),
      },
    ];
    if (!isAdmin) {
      return base;
    }
    return [
      ...base,
      { type: "divider", style: { margin: "20px 0 12px", borderColor: "rgba(255,255,255,0.14)" } },
      {
        type: "group",
        label: (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "rgba(255, 255, 255, 0.45)",
            }}
          >
            Администрирование
          </span>
        ),
        children: [
          {
            key: "/admin/users",
            icon: <TeamOutlined />,
            label: <Link to="/admin/users">Пользователи</Link>,
          },
          {
            key: "/admin/stats",
            icon: <BarChartOutlined />,
            label: <Link to="/admin/stats">Статистика</Link>,
          },
          {
            key: "/admin/ledger",
            icon: <TransactionOutlined />,
            label: <Link to="/admin/ledger">Журнал операций</Link>,
          },
        ],
      },
    ];
  }, [isAdmin]);

  function logout() {
    clearToken();
    nav("/login", { replace: true });
  }

  return (
    <Layout style={{ minHeight: "100vh", background: "transparent" }}>
      <Sider breakpoint="lg" collapsedWidth={0} width={240} theme="dark">
        <div
          style={{
            height: DASHBOARD_TOPBAR_HEIGHT,
            minHeight: DASHBOARD_TOPBAR_HEIGHT,
            boxSizing: "border-box",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 12px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              flexShrink: 0,
              background: "linear-gradient(135deg, #2ee6be, #ffb547)",
              boxShadow: "0 0 18px rgba(46, 230, 190, 0.45)",
            }}
          />
          <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Typography.Text strong style={{ color: "#f0f0f5", fontSize: 15, letterSpacing: "-0.02em" }}>
              SafeTalk
            </Typography.Text>
            {isAdmin ? (
              <Tag color="magenta" style={{ margin: 0, lineHeight: "20px" }}>
                Админ
              </Tag>
            ) : null}
          </div>
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selectedKey]} items={menuItems} style={{ borderRight: 0 }} />
      </Sider>
      <Layout style={{ background: "transparent" }}>
        <Header
          style={{
            height: DASHBOARD_TOPBAR_HEIGHT,
            minHeight: DASHBOARD_TOPBAR_HEIGHT,
            maxHeight: DASHBOARD_TOPBAR_HEIGHT,
            boxSizing: "border-box",
            lineHeight: 1,
            paddingBlock: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            paddingInline: 24,
            position: "sticky",
            top: 0,
            zIndex: 20,
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            background: "rgba(6, 6, 10, 0.75)",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <Button type="text" icon={<LogoutOutlined />} onClick={logout} style={{ color: "rgba(240, 240, 245, 0.88)" }}>
            Выйти
          </Button>
        </Header>
        <Content style={{ padding: 24, maxWidth: 1100, margin: "0 auto", width: "100%", background: "transparent" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
