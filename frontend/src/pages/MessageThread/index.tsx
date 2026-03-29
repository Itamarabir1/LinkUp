import ChatErrorBoundary from '../../components/ChatErrorBoundary/ChatErrorBoundary';
import MessageThreadPanel from './MessageThreadPanel';
import { useMessageThread } from './useMessageThread';

export interface MessageThreadProps {
  /** כשמועבר — משמש במקום useParams (להטמעה בפנל). */
  conversationId?: string;
  /** true = פנל ימני: בלי כפתור חזרה, layout ממלא את המכל. */
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
