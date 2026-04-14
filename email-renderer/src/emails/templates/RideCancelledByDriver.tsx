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
  origin?: string;
  destination?: string;
  action_url?: string;
}

export default function RideCancelledByDriver({
  passenger_name,
  origin,
  destination,
  action_url = 'https://linkup.co.il/search',
}: Props) {
  return (
    <EmailLayout
      preview="עדכון דחוף: הנסיעה שלך בוטלה"
      headerColor={COLORS.danger}
      headerTitle="עדכון דחוף: הנסיעה בוטלה"
    >
      <Text style={bodyText}>
        שלום <strong>{passenger_name}</strong>,
      </Text>
      <Text style={mutedText}>אנו מצטערים להודיע שהנסיעה המתוכננת שלך בוטלה על ידי הנהג ולא תתקיים.</Text>
      <EmailInfoBox color={COLORS.danger} rows={[{ label: 'מסלול', value: `${origin || ''} → ${destination || ''}` }]} />
      <Text style={mutedText}>אנא חפש/י נסיעה חלופית במערכת בהקדם.</Text>
      <EmailButton href={action_url} color={COLORS.primary}>
        חפש נסיעה חלופית
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
