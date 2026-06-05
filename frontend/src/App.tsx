import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import LoginPage from '@/pages/LoginPage'
import UploadPage from '@/pages/UploadPage'
import ProgressPage from '@/pages/ProgressPage'
import EditorPage from '@/pages/EditorPage'
import { useSessionStore } from '@/stores/session'
import AppHeader from '@/components/AppHeader'

function App() {
  const { token, step, reset, settings, setSettings } = useSessionStore()

  if (!token) {
    return (
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#6366f1',
            borderRadius: 8,
          },
        }}
      >
        <LoginPage />
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#6366f1',
          borderRadius: 8,
        },
      }}
    >
      <div className="min-h-screen bg-gray-50">
        <AppHeader />
        {step === 'upload' && (
          <UploadPage
            settings={settings}
            onSettingsChange={setSettings}
            onStart={() => useSessionStore.setState({ step: 'progress' })}
          />
        )}
        {step === 'progress' && (
          <ProgressPage
            settings={settings}
            onComplete={() => useSessionStore.setState({ step: 'editor' })}
            onCancel={() => reset()}
          />
        )}
        {step === 'editor' && (
          <EditorPage onReset={() => reset()} />
        )}
      </div>
    </ConfigProvider>
  )
}

export default App
