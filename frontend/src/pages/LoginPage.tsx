import { Button, Card, Form, Input, Tabs, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useState } from 'react'
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
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{
        backgroundColor: 'var(--bg-primary)',
      }}
    >
      <div className="w-full max-w-md fade-up">
        {/* Brand — editorial style */}
        <div className="text-center mb-8">
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none" className="mx-auto mb-4">
            <rect x="3" y="6" width="26" height="20" rx="2" stroke="#1c1917" strokeWidth="2" fill="none" />
            <rect x="6" y="9" width="20" height="14" rx="1" fill="#b45309" />
            <circle cx="16" cy="16" r="3" fill="#fef3c7" />
            <circle cx="16" cy="16" r="1.5" fill="#1c1917" />
          </svg>
          <Title
            level={2}
            style={{
              fontFamily: 'var(--font-display)',
              color: 'var(--ink-900)',
              fontWeight: 700,
              marginBottom: 4,
              letterSpacing: '-0.01em',
            }}
          >
            Novel<span style={{ color: 'var(--accent-700)' }}>2</span>Script
          </Title>
          <Text
            style={{
              color: 'var(--ink-500)',
              fontSize: 13,
              letterSpacing: '0.05em',
            }}
          >
            上传小说 · 智能分析 · 生成剧本
          </Text>
        </div>

        {/* Card — minimal border, warm shadow */}
        <Card
          className="fade-up fade-up-delay-1"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: 10,
            boxShadow: 'var(--shadow-md)',
          }}
          styles={{ body: { padding: 32 } }}
        >
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
                      <Input
                        prefix={<UserOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="用户名"
                        style={{ height: 44 }}
                      />
                    </Form.Item>
                    <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                      <Input.Password
                        prefix={<LockOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="密码"
                        style={{ height: 44 }}
                      />
                    </Form.Item>
                    <Form.Item className="!mb-0">
                      <Button
                        type="primary"
                        htmlType="submit"
                        loading={loading}
                        block
                        size="large"
                      >
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
                      <Input
                        prefix={<UserOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="用户名"
                        style={{ height: 44 }}
                      />
                    </Form.Item>
                    <Form.Item name="email" rules={[
                      { required: true, message: '请输入邮箱' },
                      { type: 'email' as const, message: '邮箱格式不正确' },
                    ]}>
                      <Input
                        prefix={<MailOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="邮箱"
                        style={{ height: 44 }}
                      />
                    </Form.Item>
                    <Form.Item name="password" rules={[
                      { required: true, message: '请输入密码' },
                      { min: 6, message: '密码至少6位' },
                    ]}>
                      <Input.Password
                        prefix={<LockOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="密码"
                        style={{ height: 44 }}
                      />
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
                      <Input.Password
                        prefix={<LockOutlined style={{ color: 'var(--ink-300)' }} />}
                        placeholder="确认密码"
                        style={{ height: 44 }}
                      />
                    </Form.Item>
                    <Form.Item className="!mb-0">
                      <Button
                        type="primary"
                        htmlType="submit"
                        loading={loading}
                        block
                        size="large"
                      >
                        注 册
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
            ]}
          />
        </Card>

        {/* Footer note */}
        <div className="text-center mt-6 fade-up fade-up-delay-2">
          <Text
            style={{
              fontSize: 12,
              color: 'var(--ink-500)',
              letterSpacing: '0.05em',
            }}
          >
            内部项目 · 仅限授权使用
          </Text>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
