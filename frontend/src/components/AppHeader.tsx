import { Button, Space, Typography, Dropdown } from 'antd'
import { LogoutOutlined, UserOutlined, BookOutlined } from '@ant-design/icons'
import { useSessionStore } from '@/stores/session'

const { Text } = Typography

function AppHeader() {
  const { user, logout } = useSessionStore()

  const userMenu = {
    items: [
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: logout },
    ],
  }

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
        <Space size="middle">
          <div className="w-8 h-8 bg-indigo-50 rounded-lg flex items-center justify-center">
            <BookOutlined className="text-indigo-600 text-lg" />
          </div>
          <div>
            <Text strong className="text-gray-800 text-lg tracking-wide">AI 小说转剧本</Text>
            <Text className="text-gray-400 text-xs block -mt-0.5">Novel → Screenplay</Text>
          </div>
        </Space>

        <Dropdown menu={userMenu} placement="bottomRight" trigger={['click']}>
          <Button type="text" className="text-gray-600 hover:text-indigo-600 hover:bg-indigo-50" icon={<UserOutlined />}>
            {user?.username}
          </Button>
        </Dropdown>
      </div>
    </header>
  )
}

export default AppHeader
