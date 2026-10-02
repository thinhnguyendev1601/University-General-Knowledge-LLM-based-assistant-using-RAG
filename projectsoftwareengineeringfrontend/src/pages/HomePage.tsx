/**
 * HomePage — page wrapper cho route /.
 * Ghép Header + HomePage (landing) + ChatWidget.
 */
import { Header } from '@/components/Header'
import { HomePage as HomeContent } from '@/features/home'
import { ChatWidget } from '@/features/chat'

export function HomePage() {
  return (
    <>
      <Header />
      <HomeContent />
      <ChatWidget />
    </>
  )
}
