import { Text } from '@react-email/components';
import * as React from 'react';
import EmailButton from '../components/EmailButton';
import EmailInfoBox from '../components/EmailInfoBox';
import EmailLayout from '../components/EmailLayout';

const COLORS = {
  primary: '#4F46E5',
  success: '#16a34a',
  danger: '#e11d48',
  warning: '#d97706',
  info: '#0284c7',
} as const;

interface Props {
  user_name?: string;
  passenger_name?: string;
  origin?: string;
  destination?: string;
  ride_date?: string;
  pickup_name?: string;
  passenger_destination?: string;
  num_seats?: string | number;
  action_url?: string;
}

export default function NewRideRequest({
  user_name,
  passenger_name,
  origin,
  destination,
  ride_date,
  pickup_name,
  passenger_destination,
  num_seats,
  action_url = 'https://linkup.co.il/my-bookings?tab=driver',
}: Props) {
  return (
    <EmailLayout
      preview={`${passenger_name} ביקש/ה להצטרף לנסיעה שלך`}
      headerColor={COLORS.info}
      headerTitle="בקשת הצטרפות חדשה!"
    >
      <Text style={bodyText}>
        שלום <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>
        <strong>{passenger_name}</strong> ביקש/ה להצטרף לנסיעה שלך:
      </Text>
      <EmailInfoBox
        color={COLORS.info}
        rows={[
          { label: 'מסלול', value: `${origin || ''} → ${destination || ''}` },
          { label: 'תאריך ושעה', value: ride_date || '' },
          { label: 'נקודת איסוף', value: pickup_name || '' },
          { label: 'יעד הנוסע', value: passenger_destination || '' },
          { label: 'מקומות מבוקשים', value: String(num_seats || 1) },
        ]}
      />
      <Text style={mutedText}>נא להיכנס לאפליקציה לאשר או לדחות את הבקשה.</Text>
      <EmailButton href={action_url} color={COLORS.info}>
        לטיפול בבקשה
      </EmailButton>
    </EmailLayout>
  );
}

const bodyText: React.CSSProperties = { color: '#0d0f1a', fontSize: '16px', margin: '0 0 16px' };
const mutedText: React.CSSProperties = {
  color: '#5a607a',
  fontSize: '15px',
  lineHeight: '1.6',
  margin: '0 0 16px',
};
