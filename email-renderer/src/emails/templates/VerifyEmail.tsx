import { Text } from '@react-email/components';
import * as React from 'react';
import EmailLayout from '../components/EmailLayout';
import EmailOtpBox from '../components/EmailOtpBox';

const COLORS = {
  primary: '#4F46E5',
  success: '#16a34a',
  danger: '#e11d48',
  warning: '#d97706',
  info: '#0284c7',
} as const;

interface Props {
  user_name?: string;
  first_name?: string;
  token?: string;
  code?: string;
  action_url?: string;
}

export default function VerifyEmail({ user_name, first_name, token, code }: Props) {
  const name = user_name || first_name || '';
  const otp = token || code || '------';

  return (
    <EmailLayout
      preview="אמת את כתובת המייל שלך ב-Linkup"
      headerColor={COLORS.primary}
      headerTitle="אימות כתובת המייל שלך"
    >
      <Text style={bodyText}>
        שלום <strong>{name}</strong>,
      </Text>
      <Text style={mutedText}>כמעט סיימנו! כדי להשלים את ההרשמה ל-Linkup, הזן את הקוד הבא:</Text>
      <EmailOtpBox code={otp} expiryMinutes={10} />
      <Text style={{ ...mutedText, textAlign: 'center', fontSize: '13px' }}>
        לא ביקשת? אפשר להתעלם מהודעה זו.
      </Text>
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
