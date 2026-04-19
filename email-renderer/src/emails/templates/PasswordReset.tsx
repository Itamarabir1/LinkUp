import { Section, Text } from '@react-email/components';
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
  code?: string;
  token?: string;
}

export default function PasswordReset({ user_name, code, token }: Props) {
  const otp = code || token || '------';
  return (
    <EmailLayout
      preview="קוד לאיפוס הסיסמה שלך ב-LinkUp"
      headerColor={COLORS.danger}
      headerTitle="איפוס סיסמה"
    >
      <Text style={bodyText}>
        שלום <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>קיבלנו בקשה לאיפוס הסיסמה של חשבון LinkUp שלך. הזן את הקוד הבא:</Text>
      <EmailOtpBox code={otp} expiryMinutes={10} />
      <Section
        style={{
          backgroundColor: '#fffbeb',
          borderRadius: '10px',
          padding: '14px 18px',
          borderRight: `4px solid ${COLORS.warning}`,
        }}
      >
        <Text style={{ margin: 0, color: '#92400e', fontSize: '13px' }}>
          <strong>אזהרת אבטחה:</strong> אם לא ביקשת איפוס סיסמה, התעלם מהודעה זו ושנה את הסיסמה שלך
          מיד.
        </Text>
      </Section>
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
