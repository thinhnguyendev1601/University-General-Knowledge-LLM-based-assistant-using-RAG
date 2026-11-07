/** Async server operations guard against responses from old sessions and deleted chats. */
import * as api from '@/services'
import { useChatStore } from './chatStore'

let listRequest = 0
let mutation = 0
const messageReads = new Map<string, number>()
window.addEventListener('auth-user-changed', () => messageReads.clear())
export const sessionIsCurrent = (version: number) =>
  useChatStore.getState().sessionVersion === version
export const chatExists = (id: string) =>
  useChatStore.getState().conversations.some((item) => item.id === id)

export function showChatError(error: unknown) {
  useChatStore.setState({
    error:
      error instanceof api.ApiError
        ? error.message
        : 'Không thể kết nối đến server. Vui lòng thử lại.',
  })
}

export async function loadHistory() {
  const version = useChatStore.getState().sessionVersion
  const request = ++listRequest
  const revision = mutation
  useChatStore.setState({ historyLoading: true })
  try {
    const conversations = await api.getConversations()
    if (
      !sessionIsCurrent(version) ||
      request !== listRequest ||
      revision !== mutation
    )
      return
    const active = useChatStore.getState().activeConversationId
    const activeConversationId = conversations.some(
      (item) => item.id === active
    )
      ? active
      : (conversations[0]?.id ?? null)
    useChatStore.setState((state) => ({
      conversations,
      activeConversationId,
      error: null,
      errorRequestId: null,
      messages: Object.fromEntries(
        Object.entries(state.messages).filter(([id]) =>
          conversations.some((item) => item.id === id)
        )
      ),
    }))
  } catch (error) {
    if (sessionIsCurrent(version) && request === listRequest)
      showChatError(error)
  } finally {
    if (sessionIsCurrent(version) && request === listRequest)
      useChatStore.setState({ historyLoading: false })
  }
}

export async function loadMessages(id: string, quiet = true) {
  const version = useChatStore.getState().sessionVersion
  const request = (messageReads.get(id) ?? 0) + 1
  messageReads.set(id, request)
  if (!quiet) useChatStore.setState({ messagesLoadingId: id })
  const current = () =>
    sessionIsCurrent(version) &&
    chatExists(id) &&
    messageReads.get(id) === request
  try {
    const messages = await api.getMessages(id)
    if (current()) {
      useChatStore.getState().mergeMessages(id, messages)
      const issue = useChatStore.getState().errorRequestId
      if (
        issue &&
        messages.some(
          (item) => item.role === 'assistant' && item.requestId === issue
        )
      )
        useChatStore.setState({ error: null, errorRequestId: null, retryAt: 0 })
    }
  } catch (error) {
    if (current()) {
      if (error instanceof api.ApiError && error.status === 404)
        removeLocalChat(id)
      showChatError(error)
    }
  } finally {
    if (
      sessionIsCurrent(version) &&
      useChatStore.getState().messagesLoadingId === id &&
      messageReads.get(id) === request
    )
      useChatStore.setState({ messagesLoadingId: null })
  }
}

export async function createServerConversation(): Promise<string | null> {
  const version = useChatStore.getState().sessionVersion
  ++mutation
  try {
    const conversation = await api.createConversation()
    if (!sessionIsCurrent(version)) return null
    useChatStore.getState().upsertConversation(conversation)
    useChatStore.setState((state) => ({
      activeConversationId: conversation.id,
      messages: { ...state.messages, [conversation.id]: [] },
      error: null,
    }))
    return conversation.id
  } catch (error) {
    if (sessionIsCurrent(version)) showChatError(error)
    return null
  }
}

function removeLocalChat(id: string) {
  ++mutation
  useChatStore.setState((state) => {
    const conversations = state.conversations.filter((item) => item.id !== id)
    const messages = { ...state.messages }
    delete messages[id]
    return {
      conversations,
      messages,
      activeConversationId:
        state.activeConversationId === id
          ? (conversations[0]?.id ?? null)
          : state.activeConversationId,
    }
  })
}

export async function deleteServerConversation(id: string) {
  const version = useChatStore.getState().sessionVersion
  ++mutation
  try {
    await api.deleteConversation(id)
    if (sessionIsCurrent(version)) removeLocalChat(id)
  } catch (error) {
    if (sessionIsCurrent(version)) showChatError(error)
  }
}

export async function deleteServerConversations() {
  const version = useChatStore.getState().sessionVersion
  const ids = useChatStore.getState().conversations.map((item) => item.id)
  ++mutation
  try {
    await api.deleteAllConversations()
    if (sessionIsCurrent(version)) ids.forEach(removeLocalChat)
  } catch (error) {
    if (sessionIsCurrent(version)) showChatError(error)
  }
}

export async function renameServerConversation(id: string, title: string) {
  const version = useChatStore.getState().sessionVersion
  ++mutation
  try {
    const conversation = await api.renameConversation(id, title)
    if (sessionIsCurrent(version) && chatExists(id)) {
      useChatStore.getState().upsertConversation(conversation)
      return true
    }
  } catch (error) {
    if (sessionIsCurrent(version)) showChatError(error)
  }
  return false
}
