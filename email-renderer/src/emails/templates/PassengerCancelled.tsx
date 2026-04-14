import { Text } from '@react-email/components';
import * as React from 'react';
import EmailLayout from '../components/EmailLayout';

const COLORS = {
  primary: '#4F46E5',
  success: '#16a34a',
  danger: '#e11d48',
  warning: '#d97706',
  info: '#0284c7',
} as const;

interface Props {
  driver_name?: string;
  passenger_name?: string;
  origin?: string;
  destination?: string;
}

export default function PassengerCancelled({ driver_name, passenger_name, origin, destination }: Props) {
  return (
    <EmailLayout
      preview={`${passenger_name} ביטל/ה את ההצטרפות לנסיעה`}
      headerColor={COLORS.danger}
      headerTitle="עדכון: ביטול הצטרפות"
    >
      <Text style={bodyText}>
        היי <strong>{driver_name}</strong>,
      </Text>
      <Text style={mutedText}>
        הנוסע/ת <strong>{passenger_name}</strong> ביטל/ה את הצטרפותו/ה לנסיעה מ{origin} ל{destination}.
      </Text>
      <Text style={mutedText}>המקום התפנה מחדש במערכת — נוסעים אחרים יוכלו לבקש להצטרף.</Text>
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
