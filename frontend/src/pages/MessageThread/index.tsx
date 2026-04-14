import ChatErrorBoundary from '../../components/ChatErrorBoundary/ChatErrorBoundary';
import MessageThreadPanel from './MessageThreadPanel';
import { useMessageThread } from './useMessageThread';

export interface MessageThreadProps {
  /** Optional conversation id override for embedded panel mode. */
  conversationId?: string;
  /** true = embedded panel mode (no back button, fill container). */
  embedded?: boolean;
}

function MessageThreadContent({ conversationId, embedded }: MessageThreadProps) {
  const vm = useMessageThread(conversationId);
  return <MessageThreadPanel vm={vm} embedded={embedded} />;
}

export default function MessageThread(props: MessageThreadProps = {}) {
  return (
    <ChatErrorBoundary>
      <MessageThreadContent {...props} />
    </ChatErrorBoundary>
  );
}
