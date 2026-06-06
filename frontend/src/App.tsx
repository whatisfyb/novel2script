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

  const themeConfig = {
    locale: zhCN,
    theme: {
      token: {
        colorPrimary: '#b45309',
        colorText: '#44403c',
        colorTextHeading: '#1c1917',
        colorTextSecondary: '#78716c',
        colorBorder: '#e7e5e4',
        colorBgContainer: '#ffffff',
        fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
        fontSize: 14,
        borderRadius: 6,
        borderRadiusLG: 8,
        controlHeight: 38,
        controlHeightLG: 44,
      },
      components: {
        Typography: {
          fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
          fontFamilyCode: "'JetBrains Mono', monospace",
        },
        Button: {
          fontWeight: 500,
        },
        Card: {
          borderRadiusLG: 8,
        },
      },
    },
  }

  if (!token) {
    return (
      <ConfigProvider {...themeConfig}>
        <LoginPage />
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider {...themeConfig}>
      <div className="min-h-screen">
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
