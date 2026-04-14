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
  ride_date?: string;
  driver_name?: string;
  ride_url?: string;
}

export default function RideCreatedForPassengers({
  user_name,
  origin,
  destination,
  ride_date,
  driver_name,
  ride_url = 'https://linkup.co.il/search',
}: Props) {
  return (
    <EmailLayout
      preview={`נסיעה חדשה מ${origin} ל${destination} מתאימה לך`}
      headerColor={COLORS.primary}
      headerTitle="נסיעה חדשה מתאימה לך 🚗"
    >
      <Text style={bodyText}>
        שלום <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>נרשמה נסיעה חדשה שיכולה להתאים לך:</Text>
      <EmailInfoBox
        color={COLORS.primary}
        rows={[
          { label: 'מאיפה', value: origin || '' },
          { label: 'לאן', value: destination || '' },
          { label: 'מתי', value: ride_date || '' },
          { label: 'נהג', value: driver_name || '' },
        ]}
      />
      <Text style={mutedText}>לחץ/י על הכפתור כדי לצפות בנסיעה ולבקש להצטרף.</Text>
      <EmailButton href={ride_url} color={COLORS.primary}>
        לצפייה בנסיעה ובקשת הצטרפות
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
