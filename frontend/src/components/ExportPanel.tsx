import { Button, Dropdown, message } from 'antd'
import { DownloadOutlined, DownOutlined } from '@ant-design/icons'
import type { FC } from 'react'
import yaml from 'yaml'
import { exportAsFountain } from '@/services/export'

interface Props {
  yamlText: string
}

const ExportPanel: FC<Props> = ({ yamlText }) => {
  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    message.success(`已导出: ${filename}`)
  }

  const handleExportYaml = () => {
    downloadFile(yamlText, 'screenplay.yaml', 'text/yaml')
  }

  const handleExportFountain = () => {
    try {
      const parsed = yaml.parse(yamlText)
      const fountain = exportAsFountain(parsed)
      downloadFile(fountain, 'screenplay.fountain', 'text/plain')
    } catch {
      message.error('YAML 格式错误，无法导出')
    }
  }

  const handleExportPdf = () => {
    message.info('PDF 导出功能开发中，请使用 YAML 或 Fountain 格式')
  }

  const items = [
    { key: 'yaml', label: 'YAML (.yaml)', onClick: handleExportYaml },
    { key: 'fountain', label: 'Fountain (.fountain)', onClick: handleExportFountain },
    { key: 'pdf', label: 'PDF (.pdf)', onClick: handleExportPdf, disabled: true },
  ]

  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <Button type="primary" icon={<DownloadOutlined />}>
        导出 <DownOutlined />
      </Button>
    </Dropdown>
  )
}

export default ExportPanel
