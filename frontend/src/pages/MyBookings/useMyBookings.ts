import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useGroup } from '../../context/GroupContext';
import { useChat } from '../../context/ChatContext';
import { openChatByBooking } from '../../api/chat';
import { getApiErrorMessage } from '../../utils/apiError';
import { usePassengerLocationBroadcast } from '../../hooks/usePassengerLocationBroadcast';
import type { TabKind } from './myBookings.types';
import { useMyBookingsDriver } from './useMyBookingsDriver';
import { useMyBookingsPassenger } from './useMyBookingsPassenger';

export function useMyBookings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const { myGroups } = useGroup();
  const { openChat } = useChat();

  const activeTab: TabKind = searchParams.get('tab') === 'driver' ? 'driver' : 'passenger';
  const setActiveTab = useCallback(
    (tab: TabKind) => {
      if (tab === 'driver') setSearchParams({ tab: 'driver' });
      else setSearchParams({});
    },
    [setSearchParams]
  );

  const [error, setError] = useState('');
  const passenger = useMyBookingsPassenger(user?.user_id, setError);
  const driver = useMyBookingsDriver(user, activeTab, setError);

  const [chatLoading, setChatLoading] = useState<string | null>(null);
  const [trackDriverBookingId, setTrackDriverBookingId] = useState<string | null>(null);
  const [sharingLocationBookingId, setSharingLocationBookingId] = useState<string | null>(null);

  usePassengerLocationBroadcast(sharingLocationBookingId, !!sharingLocationBookingId);

  const handleOpenChat = useCallback(
    async (bookingId: string) => {
      setChatLoading(bookingId);
      setError('');
      try {
        const conversation = await openChatByBooking(bookingId);
        openChat(conversation.conversation_id);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'פתיחת שיחה נכשלה'));
      } finally {
        setChatLoading(null);
      }
    },
    [openChat]
  );

  return {
    user,
    myGroups,
    activeTab,
    setActiveTab,
    error,
    ...passenger,
    ...driver,
    chatLoading,
    trackDriverBookingId,
    setTrackDriverBookingId,
    sharingLocationBookingId,
    setSharingLocationBookingId,
    handleOpenChat,
  };
}
