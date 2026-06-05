import Editor from '@monaco-editor/react'
import type { FC } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
}

const MonacoYaml: FC<Props> = ({ value, onChange }) => {
  return (
    <Editor
      height="100%"
      width="100%"
      language="yaml"
      value={value}
      onChange={(v) => onChange(v || '')}
      theme="light"
      options={{
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
        minimap: { enabled: false },
        wordWrap: 'on',
        automaticLayout: true,
        tabSize: 2,
        renderWhitespace: 'selection',
        scrollBeyondLastLine: false,
        lineNumbers: 'on',
        glyphMargin: false,
        folding: true,
        lineDecorationsWidth: 8,
        bracketPairColorization: { enabled: true },
        padding: { top: 12 },
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
      }}
    />
  )
}

export default MonacoYaml
