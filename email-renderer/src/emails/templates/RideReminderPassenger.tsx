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
  origin?: string;
  destination?: string;
  partner_name?: string;
  ride_url?: string;
}

export default function RideReminderPassenger({
  user_name,
  origin,
  destination,
  partner_name,
  ride_url = 'https://linkup.co.il/my-bookings',
}: Props) {
  return (
    <EmailLayout
      preview="הנסיעה שלך יוצאת בעוד חצי שעה!"
      headerColor={COLORS.warning}
      headerTitle="הנסיעה שלך יוצאת בקרוב! ⏰"
    >
      <Text style={bodyText}>
        שלום <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>תזכורת: הנסיעה שלך יוצאת בעוד כחצי שעה.</Text>
      <EmailInfoBox
        color={COLORS.warning}
        rows={[
          { label: 'מסלול', value: `${origin || ''} → ${destination || ''}` },
          { label: 'נהג', value: partner_name || '' },
        ]}
      />
      <Text style={mutedText}>זה הזמן להתארגן וליצור קשר עם הנהג אם יש שינויים אחרונים.</Text>
      <EmailButton href={ride_url} color={COLORS.warning}>
        לפרטי הנסיעה והתקשורות
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
