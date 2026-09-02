import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, theme, Drawer } from 'antd';
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  HddOutlined,
  CloudUploadOutlined,
  RobotOutlined,
  BarChartOutlined,
  ShopOutlined,
  MenuOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useIsMobile } from '../hooks/useIsMobile';

const { Header, Sider, Content } = Layout;

interface NavItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  shortLabel: string;
}

const menuItems: NavItem[] = [
  { key: '/', icon: <DashboardOutlined />, label: '经营看板', shortLabel: '看板' },
  { key: '/realtime', icon: <ThunderboltOutlined />, label: '实时销售', shortLabel: '实时' },
  { key: '/shop-daily', icon: <FileTextOutlined />, label: '店铺日报', shortLabel: '日报' },
  { key: '/sales', icon: <ShoppingCartOutlined />, label: '销售分析', shortLabel: '销售' },
  { key: '/store-channel', icon: <ShopOutlined />, label: '店铺渠道', shortLabel: '店铺' },
  { key: '/profit', icon: <DollarOutlined />, label: '利润分析', shortLabel: '利润' },
  { key: '/inventory', icon: <HddOutlined />, label: '库存健康', shortLabel: '库存' },
  { key: '/agents', icon: <RobotOutlined />, label: 'AI决策', shortLabel: 'AI' },
  { key: '/analysis', icon: <BarChartOutlined />, label: '高级分析', shortLabel: '分析' },
  { key: '/import', icon: <CloudUploadOutlined />, label: '数据导入', shortLabel: '导入' },
  { key: '/operations', icon: <SettingOutlined />, label: '运营设置', shortLabel: '设置' },
];

// Bottom tab bar shows these 4 + a "more" button
const primaryTabs = menuItems.slice(0, 4);
const secondaryTabs = menuItems.slice(4);

function getLabel(items: NavItem[], path: string): string {
  return items.find((m) => m.key === path)?.label || '经营看板';
}

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const isMobile = useIsMobile();

  const selectedKey = menuItems.find((m) => location.pathname === m.key)?.key || '/';
  const currentLabel = getLabel(menuItems, selectedKey);

  // ---- Mobile layout: bottom tab bar + simplified header ----
  if (isMobile) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <div className="mobile-header">
          <span className="mobile-header-title">{currentLabel}</span>
          <span style={{ fontSize: 12, color: token.colorTextSecondary }}>旺店通数据</span>
        </div>
        <Content style={{ overflow: 'auto', height: 'calc(100vh - 48px - 56px)' }}>
          <Outlet />
        </Content>

        {/* Bottom Tab Bar */}
        <div className="mobile-tab-bar">
          {primaryTabs.map((item) => (
            <div
              key={item.key}
              className={`mobile-tab-item ${selectedKey === item.key ? 'active' : ''}`}
              onClick={() => navigate(item.key)}
            >
              {item.icon}
              <span>{item.shortLabel}</span>
            </div>
          ))}
          {/* "More" button */}
          <div
            className={`mobile-tab-item ${secondaryTabs.some((t) => t.key === selectedKey) ? 'active' : ''}`}
            onClick={() => setDrawerOpen(true)}
          >
            <MenuOutlined />
            <span>更多</span>
          </div>
        </div>

        {/* Drawer for secondary navigation */}
        <Drawer
          title="更多功能"
          placement="bottom"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          height="auto"
          styles={{ body: { padding: '8px 0' } }}
        >
          {secondaryTabs.map((item) => (
            <div
              key={item.key}
              onClick={() => {
                navigate(item.key);
                setDrawerOpen(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '14px 24px',
                fontSize: 15,
                color: selectedKey === item.key ? '#1677ff' : '#333',
                cursor: 'pointer',
                background: selectedKey === item.key ? '#e6f4ff' : 'transparent',
              }}
            >
              <span style={{ fontSize: 20 }}>{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
        </Drawer>
      </Layout>
    );
  }

  // ---- Desktop layout: sidebar (unchanged) ----
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{ overflow: 'auto', height: '100vh', position: 'fixed', left: 0, top: 0, bottom: 0 }}
      >
        <div
          style={{
            height: 56,
            margin: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: collapsed ? 14 : 16,
            fontWeight: 700,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? 'AI' : 'AI经营决策平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems.map(({ shortLabel: _shortLabel, ...item }) => item)}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 56,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <span style={{ fontSize: 16, fontWeight: 600, color: token.colorTextHeading }}>
            {currentLabel}
          </span>
          <span style={{ fontSize: 13, color: token.colorTextSecondary }}>
            AI企业经营决策平台 · 旺店通数据
          </span>
        </Header>
        <Content style={{ overflow: 'auto', height: 'calc(100vh - 56px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
