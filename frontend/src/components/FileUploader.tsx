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
      className="!rounded-2xl !border-2 !border-dashed !border-gray-200 hover:!border-indigo-300 !bg-white !transition-all !duration-300 hover:!shadow-md"
    >
      <div className="py-8">
        <p className="mb-4">
          <span className="inline-flex items-center justify-center w-20 h-20 bg-indigo-100 rounded-2xl">
            <InboxOutlined className="text-4xl text-indigo-500" />
          </span>
        </p>
        <p className="text-lg font-medium text-gray-700 mb-1">
          点击或拖拽小说文件到此区域
        </p>
        <p className="text-gray-400">
          支持 .txt / .md / .docx 格式 · 建议 3 章以上
        </p>
      </div>
    </Dragger>
  )
}

export default FileUploader
