import MessageThreadPanel from './MessageThreadPanel';
import { useMessageThread } from './useMessageThread';

export interface MessageThreadProps {
  /** כשמועבר — משמש במקום useParams (להטמעה בפנל). */
  conversationId?: string;
  /** true = פנל ימני: בלי כפתור חזרה, layout ממלא את המכל. */
  embedded?: boolean;
}

export default function MessageThread({ conversationId, embedded }: MessageThreadProps = {}) {
  const vm = useMessageThread(conversationId);
  return <MessageThreadPanel vm={vm} embedded={embedded} />;
}
