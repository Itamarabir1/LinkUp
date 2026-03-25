import { useState } from 'react';
import { fetchAdminBooking, fetchAdminRide } from '../api/lookup';

type Result = { status: 'idle' | 'loading' | 'ready' | 'error'; data?: unknown };

export default function AdminLookup() {
  const [rideId, setRideId] = useState('');
  const [bookingId, setBookingId] = useState('');
  const [result, setResult] = useState<Result>({ status: 'idle' });

  async function run(kind: 'ride' | 'booking') {
    setResult({ status: 'loading' });
    try {
      const id = (kind === 'ride' ? rideId : bookingId).trim();
      const res = kind === 'ride' ? await fetchAdminRide(id) : await fetchAdminBooking(id);
      setResult({ status: 'ready', data: res.data });
    } catch {
      setResult({ status: 'error' });
    }
  }

  return (
    <div>
      <h3>Ride / Booking lookup</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <h4 style={{ marginTop: 0 }}>Ride</h4>
          <input
            value={rideId}
            onChange={(e) => setRideId(e.target.value)}
            placeholder="ride_id (UUID)"
            style={{ padding: 8, width: '100%' }}
          />
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => run('ride')} disabled={!rideId.trim()}>
              Fetch ride
            </button>
          </div>
        </div>
        <div>
          <h4 style={{ marginTop: 0 }}>Booking</h4>
          <input
            value={bookingId}
            onChange={(e) => setBookingId(e.target.value)}
            placeholder="booking_id (UUID)"
            style={{ padding: 8, width: '100%' }}
          />
          <div style={{ marginTop: 8 }}>
            <button type="button" onClick={() => run('booking')} disabled={!bookingId.trim()}>
              Fetch booking
            </button>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <h4>Result</h4>
        {result.status === 'idle' && <p>Enter an id and fetch.</p>}
        {result.status === 'loading' && <p>Loading…</p>}
        {result.status === 'error' && <p>Not found / failed.</p>}
        {result.status === 'ready' && (
          <pre
            style={{
              background: '#111',
              color: '#eee',
              padding: 12,
              borderRadius: 6,
              overflowX: 'auto',
              maxHeight: 460,
            }}
          >
            {JSON.stringify(result.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
