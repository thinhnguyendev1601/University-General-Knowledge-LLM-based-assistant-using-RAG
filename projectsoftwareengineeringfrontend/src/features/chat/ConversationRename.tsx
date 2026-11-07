import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui'
import styles from './ChatWidget.module.css'

interface ConversationRenameProps {
  title: string
  onSave: (title: string) => Promise<boolean>
  onCancel: () => void
}

export function ConversationRename({
  title,
  onSave,
  onCancel,
}: ConversationRenameProps) {
  const [value, setValue] = useState(title)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => {
    input.current?.focus()
    input.current?.select()
  }, [])
  return (
    <form
      className={styles.renameForm}
      onSubmit={async (event) => {
        event.preventDefault()
        if (saving || !value.trim()) return
        setSaving(true)
        const saved = await onSave(value.trim())
        setSaving(false)
        if (saved) onCancel()
        else setError(true)
      }}
    >
      <label htmlFor="conversation-title">Tên hội thoại</label>
      <input
        ref={input}
        id="conversation-title"
        value={value}
        maxLength={200}
        disabled={saving}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape' && !saving) onCancel()
        }}
      />
      {error && <p role="alert">Chưa đổi được tên. Vui lòng thử lại.</p>}
      <div className={styles.renameActions}>
        <Button size="sm" type="submit" disabled={saving || !value.trim()}>
          {saving ? 'Đang lưu...' : 'Lưu tên'}
        </Button>
        <Button size="sm" type="button" onClick={onCancel} disabled={saving}>
          Hủy
        </Button>
      </div>
    </form>
  )
}
