import { useCallback, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useGroup } from '../../context/GroupContext';
import { useChat } from '../../context/ChatContext';
import { openChatByBooking } from '../../api/chat';
import { getApiErrorMessage } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';
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
  const passenger = useMyBookingsPassenger(user?.user_id, activeTab, setError);
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
        setError(getApiErrorMessage(err, apiErr('err_open_chat')));
      } finally {
        setChatLoading(null);
      }
    },
    [openChat]
  );

  /** Grouped view-model so tabs only depend on the slice they need. */
  return {
    user,
    myGroups,
    activeTab,
    setActiveTab,
    error,
    passenger: {
      activeItems: passenger.activeItems,
      historyItems: passenger.historyItems,
      loading: passenger.passengerLoading,
      fetchMorePassengerHistory: passenger.fetchMorePassengerHistory,
      hasMorePassengerHistory: passenger.hasMorePassengerHistory,
      isFetchingPassengerHistory: passenger.isFetchingPassengerHistory,
      bookingToCancel: passenger.bookingToCancel,
      setBookingToCancel: passenger.setBookingToCancel,
      cancelling: passenger.cancelling,
      confirmCancelBooking: passenger.confirmCancelBooking,
      sharingLocationBookingId,
      setSharingLocationBookingId,
      trackDriverBookingId,
      setTrackDriverBookingId,
    },
    driver: {
      activeItems: driver.activeItems,
      historyItems: driver.historyItems,
      loading: driver.driverLoading,
      fetchMoreDriverHistory: driver.fetchMoreDriverHistory,
      hasMoreDriverHistory: driver.hasMoreDriverHistory,
      isFetchingDriverHistory: driver.isFetchingDriverHistory,
      sharingRideId: driver.sharingRideId,
      setSharingRideId: driver.setSharingRideId,
      liveRideId: driver.liveRideId,
      setLiveRideId: driver.setLiveRideId,
      rideToCancel: driver.rideToCancel,
      setRideToCancel: driver.setRideToCancel,
      cancellingRide: driver.cancellingRide,
      actionBookingId: driver.actionBookingId,
      handleShareStart: driver.handleShareStart,
      handleShareStop: driver.handleShareStop,
      handleApprove: driver.handleApprove,
      handleReject: driver.handleReject,
      confirmCancelRide: driver.confirmCancelRide,
    },
    chat: {
      loading: chatLoading,
      onOpen: handleOpenChat,
    },
  };
}

export type MyBookingsViewModel = ReturnType<typeof useMyBookings>;
