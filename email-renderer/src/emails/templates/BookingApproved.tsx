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
  passenger_name?: string;
  driver_name?: string;
  origin?: string;
  destination?: string;
  ride_date?: string;
  action_url?: string;
}

export default function BookingApproved({
  passenger_name,
  driver_name,
  origin,
  destination,
  ride_date,
  action_url = 'https://linkup.co.il/my-bookings',
}: Props) {
  return (
    <EmailLayout preview="יש לך טרמפ! ההזמנה שלך אושרה" headerColor={COLORS.success} headerTitle="יש לך טרמפ! 🎉">
      <Text style={bodyText}>
        שלום <strong>{passenger_name}</strong>,
      </Text>
      <Text style={mutedText}>
        הנהג <strong>{driver_name}</strong> אישר את הבקשה שלך לנסיעה.
      </Text>
      <EmailInfoBox
        color={COLORS.success}
        rows={[
          { label: 'מאיפה', value: origin || '' },
          { label: 'לאן', value: destination || '' },
          { label: 'תאריך', value: ride_date || '' },
        ]}
      />
      <Text style={mutedText}>מומלץ ליצור קשר עם הנהג דרך הצ׳אט לפני הנסיעה.</Text>
      <EmailButton href={action_url} color={COLORS.success}>
        לפרטי הנסיעה
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
