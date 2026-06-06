import { Upload, type UploadProps } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import type { FC } from 'react'

interface Props {
  onFileSelected: (file: File) => void
}

const { Dragger } = Upload

const FileUploader: FC<Props> = ({ onFileSelected }) => {
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.txt,.md,.docx',
    beforeUpload: (file) => {
      onFileSelected(file)
      return false
    },
    showUploadList: true,
  }

  return (
    <Dragger
      {...uploadProps}
      style={{
        borderRadius: 8,
        border: '2px dashed var(--border-strong)',
        backgroundColor: 'var(--bg-card)',
        transition: 'all 0.25s ease',
      }}
    >
      <div className="py-10">
        <p className="mb-4">
          <span
            className="inline-flex items-center justify-center"
            style={{
              width: 72,
              height: 72,
              borderRadius: 8,
              backgroundColor: 'var(--accent-100)',
            }}
          >
            <InboxOutlined
              style={{
                fontSize: 32,
                color: 'var(--accent-700)',
              }}
            />
          </span>
        </p>
        <p
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--ink-900)',
            marginBottom: 4,
          }}
        >
          点击或拖拽小说文件到此区域
        </p>
        <p
          style={{
            fontSize: 13,
            color: 'var(--ink-500)',
          }}
        >
          支持 .txt / .md / .docx 格式 · 建议 3 章以上
        </p>
      </div>
    </Dragger>
  )
}

export default FileUploader
