import { useState } from 'react'
import { Card, Tabs, Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useSessionStore } from '@/stores/session'

const { Title, Text } = Typography

function LoginPage() {
  const { login, register } = useSessionStore()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('login')

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
    } catch {
      message.error('登录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (values: { username: string; email: string; password: string }) => {
    setLoading(true)
    try {
      await register(values.username, values.email, values.password)
      message.success('注册成功')
    } catch {
      message.error('注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-8">
          <Title level={2} className="!mb-2 !text-gray-800">AI 小说转剧本</Title>
          <Text className="text-gray-400">上传小说 · 智能分析 · 生成专业剧本</Text>
        </div>

        {/* Card */}
        <Card className="shadow-sm border border-gray-100 !rounded-xl" styles={{ body: { padding: '32px' } }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            size="large"
            items={[
              {
                key: 'login',
                label: '登录',
                children: (
                  <Form onFinish={handleLogin} layout="vertical" size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                      <Input prefix={<UserOutlined className="text-gray-400" />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                      <Input.Password prefix={<LockOutlined className="text-gray-400" />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item className="!mb-0">
                      <Button type="primary" htmlType="submit" loading={loading} block size="large">
                        登 录
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: '注册',
                children: (
                  <Form onFinish={handleRegister} layout="vertical" size="large">
                    <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                      <Input prefix={<UserOutlined className="text-gray-400" />} placeholder="用户名" />
                    </Form.Item>
                    <Form.Item name="email" rules={[
                      { required: true, message: '请输入邮箱' },
                      { type: 'email', message: '邮箱格式不正确' },
                    ]}>
                      <Input prefix={<MailOutlined className="text-gray-400" />} placeholder="邮箱" />
                    </Form.Item>
                    <Form.Item name="password" rules={[
                      { required: true, message: '请输入密码' },
                      { min: 6, message: '密码至少6位' },
                    ]}>
                      <Input.Password prefix={<LockOutlined className="text-gray-400" />} placeholder="密码" />
                    </Form.Item>
                    <Form.Item name="confirmPassword" dependencies={['password']} rules={[
                      { required: true, message: '请确认密码' },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue('password') === value) return Promise.resolve()
                          return Promise.reject(new Error('两次密码不一致'))
                        },
                      }),
                    ]}>
                      <Input.Password prefix={<LockOutlined className="text-gray-400" />} placeholder="确认密码" />
                    </Form.Item>
                    <Form.Item className="!mb-0">
                      <Button type="primary" htmlType="submit" loading={loading} block size="large">
                        注 册
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
            ]}
          />
        </Card>

        {/* Footer */}
        <Text className="block text-center mt-6 text-gray-300 text-sm">
          Novel-to-Script · Powered by AI
        </Text>
      </div>
    </div>
  )
}

export default LoginPage
