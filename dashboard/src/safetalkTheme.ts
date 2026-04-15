import type { ThemeConfig } from "antd";
import { theme } from "antd";

/**
 * Токены в духе `static/index.htm`: тёмный фон, акцент #2ee6be, Outfit.
 */
export const safetalkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    borderRadius: 14,
    borderRadiusLG: 14,
    borderRadiusSM: 10,
    colorPrimary: "#2ee6be",
    colorLink: "#2ee6be",
    colorInfo: "#2ee6be",
    colorWarning: "#ffb547",
    colorError: "#ff6b6b",
    colorBgBase: "#06060a",
    colorBgLayout: "#06060a",
    colorBgContainer: "#14141f",
    colorBgElevated: "#1a1a2a",
    colorBorder: "rgba(255, 255, 255, 0.08)",
    colorBorderSecondary: "rgba(255, 255, 255, 0.06)",
    colorText: "#f0f0f5",
    colorTextSecondary: "#9898ac",
    colorTextTertiary: "#8a8a9e",
    colorTextQuaternary: "#7a7a8e",
    fontFamily: `'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
    fontFamilyCode: `'JetBrains Mono', ui-monospace, monospace`,
    boxShadowSecondary: "0 24px 80px rgba(0, 0, 0, 0.55)",
  },
  components: {
    Layout: {
      bodyBg: "#06060a",
      headerBg: "rgba(6, 6, 10, 0.88)",
      footerBg: "#06060a",
      siderBg: "#0e0e16",
      triggerBg: "#14141f",
      triggerColor: "#f0f0f5",
    },
    Menu: {
      darkItemBg: "#0e0e16",
      darkSubMenuItemBg: "#0a0a12",
      darkItemHoverBg: "rgba(46, 230, 190, 0.08)",
      darkItemSelectedBg: "rgba(46, 230, 190, 0.12)",
      darkItemSelectedColor: "#2ee6be",
    },
    Card: {
      colorBgContainer: "#14141f",
      headerBg: "transparent",
    },
    Button: {
      primaryShadow: "0 8px 32px rgba(46, 230, 190, 0.22)",
    },
    Table: {
      headerBg: "#1a1a2a",
      rowHoverBg: "rgba(46, 230, 190, 0.06)",
    },
    Input: {
      colorBgContainer: "#1a1a2a",
      activeShadow: "0 0 0 2px rgba(46, 230, 190, 0.15)",
    },
    Select: {
      colorBgContainer: "#1a1a2a",
    },
    Modal: {
      contentBg: "#14141f",
      headerBg: "#14141f",
      footerBg: "#14141f",
    },
    Typography: {
      colorLink: "#2ee6be",
      colorLinkHover: "#5aebce",
      colorLinkActive: "#24c9a6",
    },
  },
};
