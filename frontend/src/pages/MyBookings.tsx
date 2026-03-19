import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MapPin, MessageCircle, Navigation } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useGroup } from '../context/GroupContext';
import { useChat } from '../context/ChatContext';
import { api, openChatByBooking } from '../api/client';
import type { Ride } from '../types/api';
import { formatRideDate } from '../utils/date';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import LiveMapModal from '../components/LiveMapModal';
import LiveRideMapModal from '../components/LiveRideMapModal';
import { usePassengerLocationBroadcast } from '../hooks/usePassengerLocationBroadcast';
import { useLocationBroadcast } from '../hooks/useLocationBroadcast';
import styles from './MyBookings.module.css';

interface BookingRow {
  booking_id: string;
  ride_id: string;
  request_id: string;
  passenger_id: string;
  num_seats: number;
  status: string;
  reminder_sent?: boolean;
  created_at?: string;
  passenger_name?: string;
  phone?: string;
}

/** הזמנות שבהן אני נוסע – מבוקינג + פרטי נסיעה + שם נהג */
interface PassengerBookingItem {
  ride: Ride;
  bookingId: string;
  bookingStatus: string;
  driverName: string | null;
}

/** נוסע בנסיעה שלי (כנהג) */
interface PassengerInRide {
  bookingId: string;
  passengerName: string;
  numSeats: number;
  status: string;
  pickupName?: string | null;
  pickupTime?: string | null;
  /** יעד הבקשה של הנוסע (מ-passenger_request) */
  dropoffName?: string | null;
}

/** הזמנות שבהן אני נהג – נסיעה עם כל הנוסעים שלה */
interface DriverBookingItem {
  ride: Ride;
  passengers: PassengerInRide[];
}

type TabKind = 'driver' | 'passenger';

const AVATAR_COLORS = ['#6366f1', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0ea5e9'];

const canPassengerShare = (bookingStatus: string, rideStatus: string) =>
  bookingStatus === 'confirmed' && rideStatus === 'active';

const canDriverShare = (confirmedCount: number) => confirmedCount >= 1;

const canDriverOpenMap = (confirmedCount: number) => confirmedCount >= 1;

function getSource(ride: Ride, myGroups: { group_id: string; name: string }[]): string {
  if (!ride.group_id) return 'ציבורי';
  const g = myGroups.find((x) => x.group_id === ride.group_id);
  return g?.name ?? 'ציבורי';
}

function avatarInitial(name: string): string {
  return (name || 'נ').charAt(0).toUpperCase();
}

export default function MyBookings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();
  const { myGroups } = useGroup();
  const { openChat } = useChat();
  const activeTab: TabKind = searchParams.get('tab') === 'driver' ? 'driver' : 'passenger';
  const setActiveTab = (tab: TabKind) => {
    if (tab === 'driver') setSearchParams({ tab: 'driver' });
    else setSearchParams({});
  };
  const [passengerList, setPassengerList] = useState<PassengerBookingItem[]>([]);
  const [driverList, setDriverList] = useState<DriverBookingItem[]>([]);
  const [passengerLoading, setPassengerLoading] = useState(true);
  const [driverLoading, setDriverLoading] = useState(false);
  const [error, setError] = useState('');
  const [chatLoading, setChatLoading] = useState<string | null>(null);
  const [bookingToCancel, setBookingToCancel] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [actionBookingId, setActionBookingId] = useState<string | null>(null);
  const [trackDriverBookingId, setTrackDriverBookingId] = useState<string | null>(null);
  const [sharingLocationBookingId, setSharingLocationBookingId] = useState<string | null>(null);
  const [sharingRideId, setSharingRideId] = useState<string | null>(null);
  const [liveRideId, setLiveRideId] = useState<string | null>(null);
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancellingRide, setCancellingRide] = useState(false);

  usePassengerLocationBroadcast(sharingLocationBookingId, !!sharingLocationBookingId);

  const fetchPassengerBookings = useCallback(async () => {
    if (!user?.user_id) return;
    setPassengerLoading(true);
    setError('');
    try {
      const { data } = await api.get<BookingRow[]>('/bookings/my-bookings', {
        params: { user_id: user.user_id, limit: 50 },
      });
      const bookings = Array.isArray(data) ? data : [];
      const asPassenger = (Array.isArray(bookings) ? bookings : []).filter(
        (b) => b.passenger_id === user.user_id && (b.status === 'pending_approval' || b.status === 'confirmed')
      );
      const byRideId = new Map<string, BookingRow>();
      asPassenger.forEach((b) => {
        if (!byRideId.has(b.ride_id)) byRideId.set(b.ride_id, b);
      });
      const rideIds = Array.from(byRideId.keys());
      const items: PassengerBookingItem[] = [];
      await Promise.all(
        rideIds.map(async (rideId) => {
          try {
            const [rideRes, driverRes] = await Promise.all([
              api.get<Ride>(`/rides/${rideId}`),
              api.get<{ full_name: string }>(`/passenger/rides/${rideId}/driver-info`).catch(() => null),
            ]);
            const ride = rideRes.data;
            if (ride.status === 'cancelled') return;
            const booking = byRideId.get(rideId)!;
            items.push({
              ride,
              bookingId: booking.booking_id,
              bookingStatus: booking.status,
              driverName: driverRes?.data?.full_name ?? null,
            });
          } catch {
            // skip
          }
        })
      );
      items.sort((a, b) => new Date(a.ride.departure_time).getTime() - new Date(b.ride.departure_time).getTime());
      setPassengerList(items);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'טעינת ההזמנות נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setPassengerLoading(false);
    }
  }, [user?.user_id]);

  const fetchDriverBookings = useCallback(async () => {
    if (!user?.user_id) return;
    setDriverLoading(true);
    setError('');
    try {
      const { data: myRides } = await api.get<Ride[]>('/rides/me');
      const activeRides = (Array.isArray(myRides) ? myRides : []).filter((r) => r.status !== 'cancelled');
      const items: DriverBookingItem[] = [];
      await Promise.all(
        activeRides.map(async (ride) => {
          try {
            const manifestRes = await api.get<{
              passengers: Array<{
                booking_id: string;
                passenger_name: string;
                num_seats: number;
                status: string;
                pickup_name?: string | null;
                pickup_time?: string | null;
                destination_name?: string | null;
              }>;
            }>(`/bookings/ride/${ride.ride_id}/manifest`, {
              params: { driver_id: user.user_id },
            });
            const passengers = manifestRes.data?.passengers ?? [];
            const filteredPassengers = passengers
              .filter((p) => p.status === 'pending_approval' || p.status === 'confirmed')
              .map((p) => ({
                bookingId: p.booking_id,
                passengerName: p.passenger_name ?? 'נוסע',
                numSeats: p.num_seats,
                status: p.status,
                pickupName: p.pickup_name ?? null,
                pickupTime: p.pickup_time ?? null,
                dropoffName: p.destination_name ?? null,
              }));
            
            // רק אם יש נוסעים - נוסיף את הנסיעה לרשימה
            if (filteredPassengers.length > 0) {
              items.push({
                ride,
                passengers: filteredPassengers,
              });
            }
          } catch {
            // skip ride
          }
        })
      );
      items.sort((a, b) => new Date(a.ride.departure_time).getTime() - new Date(b.ride.departure_time).getTime());
      setDriverList(items);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'טעינת ההזמנות נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setDriverLoading(false);
    }
  }, [user?.user_id]);

  const handleShareStart = useCallback(
    async (rideId: string) => {
      setError('');
      try {
        await api.post(`/rides/${rideId}/start`);
        await fetchDriverBookings();
      } catch (err: unknown) {
        const res = (err as { response?: { status?: number; data?: { detail?: string; error_code?: string } } })
          ?.response;
        const code = res?.data?.error_code;
        const detail = typeof res?.data?.detail === 'string' ? res.data.detail : '';
        /** נסיעה כבר ACTIVE — ממשיכים לשלוח מיקום בלי לחסום את ה-watch */
        if (
          res?.status === 400 &&
          (code === 'RIDE_INVALID_STATUS' || /active|ACTIVE|פעיל/i.test(detail))
        ) {
          await fetchDriverBookings();
          return;
        }
        const msg = detail || 'התחלת הנסיעה נכשלה';
        setError(msg);
        throw err;
      }
    },
    [fetchDriverBookings]
  );

  const handleShareStop = useCallback(
    async (rideId: string) => {
      try {
        await api.post(`/rides/${rideId}/end`);
        setLiveRideId((prev) => (prev === rideId ? null : prev));
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 400) return;
        console.error('handleShareStop error:', err);
      } finally {
        await fetchDriverBookings();
      }
    },
    [fetchDriverBookings]
  );

  const driverShareConfirmedBookingId = useMemo(() => {
    if (!sharingRideId) return null;
    const block = driverList.find((d) => d.ride.ride_id === sharingRideId);
    return block?.passengers.find((p) => p.status === 'confirmed')?.bookingId ?? null;
  }, [sharingRideId, driverList]);

  useLocationBroadcast({
    rideId: sharingRideId,
    driverId: user?.user_id ?? null,
    bookingId: driverShareConfirmedBookingId,
    enabled:
      !!sharingRideId && !!user?.user_id && !!driverShareConfirmedBookingId,
    onStart: handleShareStart,
    onStop: handleShareStop,
  });

  useEffect(() => {
    fetchPassengerBookings();
  }, [fetchPassengerBookings]);

  useEffect(() => {
    if (activeTab === 'driver') fetchDriverBookings();
  }, [activeTab, fetchDriverBookings]);

  const handleOpenChat = async (bookingId: string) => {
    setChatLoading(bookingId);
    setError('');
    try {
      const conversation = await openChatByBooking(bookingId);
      openChat(conversation.conversation_id);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'פתיחת שיחה נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setChatLoading(null);
    }
  };

  const handleApprove = async (bookingId: string) => {
    if (!user?.user_id) return;
    setActionBookingId(bookingId);
    setError('');
    try {
      await api.patch(`/bookings/${bookingId}/approve`, {}, { params: { driver_id: user.user_id } });
      await fetchDriverBookings();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'אישור הבקשה נכשל';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setActionBookingId(null);
    }
  };

  const handleReject = async (bookingId: string) => {
    if (!user?.user_id) return;
    setActionBookingId(bookingId);
    setError('');
    try {
      await api.patch(`/bookings/${bookingId}/reject`, {}, { params: { driver_id: user.user_id } });
      await fetchDriverBookings();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'דחיית הבקשה נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setActionBookingId(null);
    }
  };

  const statusLabel: Record<string, string> = {
    pending_approval: 'ממתין לאישור',
    confirmed: 'אושר',
    rejected: 'נדחה',
    cancelled: 'בוטל',
  };

  return (
    <div className={styles.page}>
      <div role="tablist" className={styles.pageTabs}>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'passenger'}
          className={activeTab === 'passenger' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('passenger')}
        >
          אני נוסע
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'driver'}
          className={activeTab === 'driver' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('driver')}
        >
          אני נהג
        </button>
      </div>

      {error && <p className={styles.pageError}>{error}</p>}

      {activeTab === 'passenger' && (
        <div className={styles.cardList}>
          {passengerLoading ? (
            <p className={styles.pageLoading}>טוען...</p>
          ) : passengerList.length === 0 ? (
            <p className={styles.emptyText}>אין הזמנות כנוסע. חפש טרמפ ובקש להצטרף.</p>
          ) : (
            passengerList.map(({ ride, bookingId, bookingStatus, driverName }) => (
              <div key={bookingId} className={styles.bookingCard}>
                <div className={styles.cardRoute}>
                  {ride.origin_name ?? '?'} ← {ride.destination_name ?? '?'}
                </div>
                <div className={styles.cardMeta}>
                  {formatRideDate(ride.departure_time)} · {statusLabel[bookingStatus] ?? bookingStatus}
                </div>
                {driverName && <div className={styles.cardMeta}>נהג: {driverName}</div>}
                <div className={styles.cardMeta}>{getSource(ride, myGroups)}</div>
                {(ride.group_name ?? (ride.group_id ? getSource(ride, myGroups) : null)) && (
                  <div className={styles.cardTagWrap}>
                    <span className={styles.groupTag}>
                      {ride.group_name ?? getSource(ride, myGroups)}
                    </span>
                  </div>
                )}
                {(bookingStatus === 'pending_approval' || bookingStatus === 'confirmed') && (
                  <div className={styles.bookingCardActions}>
                    {canPassengerShare(bookingStatus, ride.status) ? (
                      <>
                        <button
                          type="button"
                          className={`${styles.btnOutline} ${
                            sharingLocationBookingId === bookingId ? styles.btnAccentGreen : ''
                          }`}
                          onClick={() =>
                            setSharingLocationBookingId((prev) => (prev === bookingId ? null : bookingId))
                          }
                        >
                          <Navigation size={15} />
                          {sharingLocationBookingId === bookingId ? 'הפסק שיתוף' : 'שתף מיקום'}
                        </button>
                        <button
                          type="button"
                          className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                          onClick={() => setTrackDriverBookingId(bookingId)}
                        >
                          <MapPin size={15} /> מפה
                        </button>
                        <button
                          type="button"
                          className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                          onClick={() => setBookingToCancel(bookingId)}
                          disabled={cancelling}
                        >
                          בטל
                        </button>
                        <button
                          type="button"
                          className={styles.btnOutline}
                          onClick={() => handleOpenChat(bookingId)}
                          disabled={chatLoading === bookingId}
                        >
                          <MessageCircle size={15} />
                          צ&apos;אט
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className={styles.btnOutline}
                          onClick={() => handleOpenChat(bookingId)}
                          disabled={chatLoading === bookingId}
                        >
                          <MessageCircle size={15} />
                          צ&apos;אט
                        </button>
                        <button
                          type="button"
                          className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                          onClick={() => setBookingToCancel(bookingId)}
                          disabled={cancelling}
                        >
                          בטל הזמנה
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'driver' && (
        <div className={styles.cardList}>
          {driverLoading ? (
            <p className={styles.pageLoading}>טוען...</p>
          ) : driverList.length === 0 ? (
            <p className={styles.emptyText}>אין הזמנות שאישרת. נוסעים שאישרת יופיעו כאן.</p>
          ) : (
            driverList.map(({ ride, passengers }) => {
              const pendingCount = passengers.filter((p) => p.status === 'pending_approval').length;
              const confirmedCount = passengers.filter((p) => p.status === 'confirmed').length;
              return (
                <div key={ride.ride_id} className={styles.driverBlock}>
                  <div className={styles.driverBlockHeader}>
                    <div className={styles.cardRoute}>
                      {ride.origin_name ?? '?'} ← {ride.destination_name ?? '?'}
                    </div>
                    <div className={styles.cardMeta}>
                      {formatRideDate(ride.departure_time)} · {ride.available_seats} מושבים פנויים
                    </div>
                    <div className={styles.driverBlockCounts}>
                      {pendingCount > 0 && <span>{pendingCount} בקשות</span>}
                      {confirmedCount > 0 && (
                        <span className={pendingCount > 0 ? styles.countSep : ''}>
                          {confirmedCount} מאושרים
                        </span>
                      )}
                    </div>
                    <div className={styles.driverBlockTagWrap}>
                      {(ride.group_name ?? (ride.group_id ? getSource(ride, myGroups) : null)) ? (
                        <span className={styles.groupTag}>
                          {ride.group_name ?? getSource(ride, myGroups)}
                        </span>
                      ) : (
                        <span className={styles.groupTagPublic}>ציבורי</span>
                      )}
                    </div>
                    <div className={styles.driverBlockActions}>
                      {canDriverShare(confirmedCount) && (
                        <>
                          <button
                            type="button"
                            className={`${styles.btnOutline} ${
                              sharingRideId === ride.ride_id ? styles.btnAccentBlueActive : ''
                            }`}
                            onClick={() =>
                              setSharingRideId((prev) => (prev === ride.ride_id ? null : ride.ride_id))
                            }
                          >
                            <Navigation size={15} />
                            {sharingRideId === ride.ride_id ? 'הפסק שיתוף' : 'שתף מיקום'}
                          </button>
                          {ride.status === 'active' ? (
                            <button
                              type="button"
                              className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                              onClick={() => handleShareStop(ride.ride_id)}
                            >
                              ■ סיים נסיעה
                            </button>
                          ) : (
                            <button
                              type="button"
                              className={styles.btnOutline}
                              onClick={() => handleShareStart(ride.ride_id)}
                            >
                              ▶ התחל נסיעה
                            </button>
                          )}
                          {canDriverOpenMap(confirmedCount) && (
                            <button
                              type="button"
                              className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                              onClick={() => setLiveRideId(ride.ride_id)}
                            >
                              <MapPin size={15} /> מפה
                            </button>
                          )}
                        </>
                      )}
                      <button
                        type="button"
                        className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                        onClick={() => setRideToCancel(ride.ride_id)}
                      >
                        בטל נסיעה
                      </button>
                    </div>
                  </div>
                  <ul className={styles.passengerList}>
                    {passengers.map((passenger) => (
                      <li key={passenger.bookingId} className={styles.passengerRow}>
                        <div
                          className={styles.passengerAvatar}
                          style={{
                            backgroundColor: AVATAR_COLORS[
                              Math.abs(passenger.passengerName.length) % AVATAR_COLORS.length
                            ],
                          }}
                        >
                          {avatarInitial(passenger.passengerName)}
                        </div>
                        <div className={styles.passengerInfo}>
                          <div className={styles.passengerName}>{passenger.passengerName}</div>
                          <div className={styles.passengerMeta}>
                            {passenger.numSeats} מושבים
                            {passenger.pickupName
                              ? ` · עולה: ${passenger.pickupName}`
                              : ''}
                            {passenger.dropoffName
                              ? ` · יורד: ${passenger.dropoffName}`
                              : ''}
                          </div>
                        </div>
                        <div className={styles.passengerActions}>
                          {passenger.status === 'pending_approval' && (
                            <div className={styles.passengerPendingActions}>
                              <button
                                type="button"
                                className={`${styles.btnOutline} ${styles.btnAccentGreen}`}
                                onClick={() => handleApprove(passenger.bookingId)}
                                disabled={actionBookingId === passenger.bookingId}
                              >
                                ✅ אשר
                              </button>
                              <button
                                type="button"
                                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                                onClick={() => handleReject(passenger.bookingId)}
                                disabled={actionBookingId === passenger.bookingId}
                              >
                                ❌ דחה
                              </button>
                              <button
                                type="button"
                                className={styles.btnOutline}
                                onClick={() => handleOpenChat(passenger.bookingId)}
                                disabled={chatLoading === passenger.bookingId}
                              >
                                <MessageCircle size={15} />
                                צ&apos;אט
                              </button>
                            </div>
                          )}
                          {passenger.status === 'confirmed' && (
                            <>
                              <span className={styles.statusConfirmed}>מאושר</span>
                              <button
                                type="button"
                                className={styles.btnOutline}
                                onClick={() => handleOpenChat(passenger.bookingId)}
                                disabled={chatLoading === passenger.bookingId}
                              >
                                <MessageCircle size={15} />
                                צ&apos;אט
                              </button>
                            </>
                          )}
                          {passenger.status === 'rejected' && (
                            <span className={styles.statusRejected}>נדחה</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })
          )}
        </div>
      )}

      <ConfirmModal
        open={bookingToCancel != null}
        onClose={() => setBookingToCancel(null)}
        title="האם אתה בטוח שאתה רוצה לבטל את ההזמנה הזו?"
        confirmLabel="אישור"
        variant="danger"
        loading={cancelling}
        onConfirm={async () => {
          if (bookingToCancel == null) return;
          setCancelling(true);
          setError('');
          try {
            await api.post(`/bookings/${bookingToCancel}/cancel`);
            setBookingToCancel(null);
            await fetchPassengerBookings();
          } catch (err: unknown) {
            const msg =
              (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
              'ביטול ההזמנה נכשל';
            setError(typeof msg === 'string' ? msg : String(msg));
          } finally {
            setCancelling(false);
          }
        }}
        titleId="confirm-cancel-booking-title"
      />

      <ConfirmModal
        open={rideToCancel != null}
        onClose={() => setRideToCancel(null)}
        title="האם אתה בטוח שאתה רוצה לבטל את הנסיעה?"
        confirmLabel="אישור"
        variant="danger"
        loading={cancellingRide}
        onConfirm={async () => {
          if (rideToCancel == null) return;
          setCancellingRide(true);
          setError('');
          try {
            await api.delete(`/rides/${rideToCancel}/cancel`);
            if (sharingRideId === rideToCancel) setSharingRideId(null);
            setLiveRideId((prev) => (prev === rideToCancel ? null : prev));
            setRideToCancel(null);
            await fetchDriverBookings();
          } catch (err: unknown) {
            const msg =
              (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
              'ביטול הנסיעה נכשל';
            setError(typeof msg === 'string' ? msg : String(msg));
          } finally {
            setCancellingRide(false);
          }
        }}
        titleId="confirm-cancel-ride-mybookings"
      />

      {trackDriverBookingId && (
        <LiveMapModal
          bookingId={trackDriverBookingId}
          onClose={() => setTrackDriverBookingId(null)}
        />
      )}

      {liveRideId && user && (
        <LiveRideMapModal
          rideId={liveRideId}
          driverId={user.user_id}
          broadcastToServer={false}
          onClose={() => setLiveRideId(null)}
        />
      )}
    </div>
  );
}
