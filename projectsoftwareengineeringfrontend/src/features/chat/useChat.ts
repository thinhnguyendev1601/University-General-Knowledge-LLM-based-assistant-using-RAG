/** Send/retry retain a request UUID; all late responses are scoped to the login session. */
import { useCallback, useEffect, useRef } from 'react'
import { ApiError, getConversation, sendMessage } from '@/services'
import type { ChatMessage } from '@/types'
import { useChatStore } from './chatStore'
import {
  chatExists,
  createServerConversation,
  loadHistory,
  loadMessages,
  sessionIsCurrent,
} from './chatHistory'

const ERROR_MESSAGE = 'Không thể kết nối đến server. Vui lòng thử lại.'

export function useChat(isOpen = true) {
  const polling = useRef<{ id: string; until: number } | null>(null)
  const ownerId = useChatStore((state) => state.ownerId)
  const activeId = useChatStore((state) => state.activeConversationId)
  const isLoading = useChatStore((state) => state.isLoading)
  const messages = useChatStore((state) =>
    activeId ? state.messages[activeId] : undefined
  )
  const pending = messages?.some(
    (item) => item.role === 'user' && item.deliveryStatus === 'pending'
  )

  useEffect(() => {
    if (ownerId) void loadHistory()
  }, [ownerId])
  useEffect(() => {
    if (ownerId && activeId) void loadMessages(activeId, false)
  }, [ownerId, activeId])
  useEffect(() => {
    if (!isOpen || !pending) polling.current = null
    if (!isOpen || !ownerId || !activeId || !pending || isLoading) return
    if (polling.current?.id !== activeId)
      polling.current = { id: activeId, until: Date.now() + 300000 }
    if (Date.now() >= polling.current.until) return
    const timer = setTimeout(() => void loadMessages(activeId), 2000)
    return () => clearTimeout(timer)
  }, [ownerId, activeId, pending, isLoading, messages, isOpen])

  const requestReply = useCallback(async (question: ChatMessage) => {
    const state = useChatStore.getState()
    const version = state.sessionVersion
    const id = question.conversationId
    if (!question.requestId) return false
    const current = () => sessionIsCurrent(version) && chatExists(id)
    useChatStore.setState({
      error: null,
      errorRequestId: null,
      isLoading: true,
      pendingConversationId: id,
      retryAt: 0,
    })
    state.mergeMessages(id, [
      { ...question, deliveryStatus: 'pending', errorCode: null },
    ])
    try {
      const reply = await sendMessage(
        id,
        question.content,
        question.requestId,
        question.institutionId ?? undefined
      )
      if (!current()) return false
      useChatStore
        .getState()
        .mergeMessages(id, [
          { ...question, deliveryStatus: 'completed' },
          reply,
        ])
      return true
    } catch (error) {
      if (current()) {
        const busy = error instanceof ApiError && error.status === 409
        useChatStore
          .getState()
          .mergeMessages(id, [
            { ...question, deliveryStatus: busy ? 'pending' : 'failed' },
          ])
        useChatStore.setState({
          error: error instanceof ApiError ? error.message : ERROR_MESSAGE,
          errorRequestId: question.requestId,
          retryAt:
            Date.now() +
            (error instanceof ApiError
              ? (error.retryAfterSeconds ?? 0) * 1000
              : 0),
        })
      }
      return false
    } finally {
      if (current()) {
        await Promise.allSettled([
          loadMessages(id),
          getConversation(id).then((conversation) => {
            if (current())
              useChatStore.getState().upsertConversation(conversation)
          }),
        ])
      }
      if (sessionIsCurrent(version))
        useChatStore.setState({ isLoading: false, pendingConversationId: null })
    }
  }, [])

  const send = useCallback(
    async (raw: string) => {
      const content = raw.trim()
      const state = useChatStore.getState()
      if (!content || !state.ownerId || state.isLoading || state.historyLoading)
        return false
      const version = state.sessionVersion
      useChatStore.setState({ isLoading: true })
      const id =
        state.activeConversationId ?? (await createServerConversation())
      if (!sessionIsCurrent(version)) return false
      if (!id) {
        useChatStore.setState({ isLoading: false })
        return false
      }
      const requestId = crypto.randomUUID()
      const question: ChatMessage = {
        id: `pending-${requestId}`,
        conversationId: id,
        requestId,
        content,
        role: 'user',
        createdAt: new Date().toISOString(),
        deliveryStatus: 'pending',
      }
      await requestReply(question)
      return true // The question is represented in history, even when generation failed.
    },
    [requestReply]
  )

  const retry = useCallback(async () => {
    const state = useChatStore.getState()
    if (state.isLoading || Date.now() < state.retryAt) return
    const id = state.activeConversationId
    const question = id
      ? [...(state.messages[id] ?? [])]
          .reverse()
          .find(
            (item) =>
              item.role === 'user' &&
              item.requestId &&
              item.deliveryStatus !== 'completed'
          )
      : undefined
    if (question) await requestReply(question)
    else {
      await loadHistory()
      const active = useChatStore.getState().activeConversationId
      if (active) await loadMessages(active)
    }
  }, [requestReply])

  return { send, retry, isLoading }
}
