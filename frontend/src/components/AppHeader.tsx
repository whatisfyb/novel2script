import { Button, Space, Typography, Dropdown } from 'antd'
import { LogoutOutlined, UserOutlined, HistoryOutlined, UploadOutlined } from '@ant-design/icons'
import { useSessionStore } from '@/stores/session'

const { Text } = Typography

function AppHeader() {
  const { user, logout, step, setStep } = useSessionStore()

  const userMenu = {
    items: [
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
    ],
  }

  const navItems = [
    { key: 'upload', label: '转换', icon: <UploadOutlined /> },
    { key: 'history', label: '历史', icon: <HistoryOutlined /> },
  ] as const

  return (
    <header
      className="border-b"
      style={{
        backgroundColor: 'var(--bg-header)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderColor: 'var(--border-color)',
      }}
    >
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
        <Space size="middle" align="center">
          {/* Logo mark */}
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => setStep('upload')}
            style={{ userSelect: 'none' }}
          >
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <rect x="3" y="6" width="26" height="20" rx="2" stroke="#1c1917" strokeWidth="2" fill="none" />
              <rect x="6" y="9" width="20" height="14" rx="1" fill="#b45309" />
              <circle cx="16" cy="16" r="3" fill="#fef3c7" />
              <circle cx="16" cy="16" r="1.5" fill="#1c1917" />
            </svg>
            <div>
              <Text
                strong
                style={{
                  fontFamily: 'var(--font-display)',
                  fontSize: 18,
                  color: 'var(--ink-900)',
                  letterSpacing: '-0.01em',
                }}
              >
                Novel<span style={{ color: 'var(--accent-700)' }}>2</span>Script
              </Text>
              <Text
                style={{
                  fontSize: 11,
                  color: 'var(--ink-500)',
                  display: 'block',
                  marginTop: -2,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                小说 · 剧本
              </Text>
            </div>
          </div>

          {/* Navigation */}
          <div
            style={{
              width: 1,
              height: 28,
              backgroundColor: 'var(--border-color)',
              marginInline: 8,
            }}
          />
          <Space size="small">
            {navItems.map((item) => {
              const isActive = step === item.key
              return (
                <Button
                  key={item.key}
                  type="text"
                  icon={item.icon}
                  onClick={() => setStep(item.key)}
                  style={{
                    color: isActive ? 'var(--ink-900)' : 'var(--ink-500)',
                    fontWeight: isActive ? 600 : 400,
                    position: 'relative',
                  }}
                >
                  {item.label}
                  {isActive && (
                    <div
                      style={{
                        position: 'absolute',
                        bottom: -2,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        width: 20,
                        height: 2,
                        backgroundColor: 'var(--accent-700)',
                        borderRadius: 1,
                      }}
                    />
                  )}
                </Button>
              )
            })}
          </Space>
        </Space>

        <Dropdown menu={userMenu} placement="bottomRight" trigger={['click']}>
          <Button
            type="text"
            icon={<UserOutlined />}
            style={{
              color: 'var(--ink-700)',
              fontWeight: 500,
            }}
          >
            {user?.username}
          </Button>
        </Dropdown>
      </div>
    </header>
  )
}

export default AppHeader
