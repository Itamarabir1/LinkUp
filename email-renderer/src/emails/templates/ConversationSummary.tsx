import { Section, Text } from '@react-email/components';
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
  user_name?: string;
  driver_name?: string;
  passenger_name?: string;
  pickup_location?: string;
  meeting_time?: string;
  summary_hebrew?: string;
}

export default function ConversationSummary({
  user_name,
  driver_name,
  passenger_name,
  pickup_location,
  meeting_time,
  summary_hebrew,
}: Props) {
  return (
    <EmailLayout preview="סיכום השיחה שלך ב-LinkUp" headerColor={COLORS.primary} headerTitle="סיכום שיחה - LinkUp">
      <Text style={bodyText}>
        שלום <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>השיחה שלך הסתיימה. הנה סיכום של הפרטים שסוכמו:</Text>
      <Section
        style={{
          backgroundColor: '#f8f9fc',
          borderRadius: '10px',
          borderRight: `4px solid ${COLORS.primary}`,
          padding: '16px 20px',
          margin: '20px 0',
        }}
      >
        <Text style={{ fontWeight: '700', color: COLORS.primary, fontSize: '15px', margin: '0 0 12px' }}>
          פרטי הנסיעה
        </Text>
        {[
          ['נהג', driver_name],
          ['נוסע', passenger_name],
          ['מיקום איסוף', pickup_location],
          ['זמן פגישה', meeting_time],
        ]
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <Text key={k as string} style={{ margin: '4px 0', fontSize: '14px', color: '#0d0f1a' }}>
              <span style={{ color: '#5a607a' }}>{k}: </span>
              <strong>{v}</strong>
            </Text>
          ))}
      </Section>
      {summary_hebrew && (
        <Section
          style={{
            backgroundColor: '#fffbeb',
            borderRadius: '10px',
            borderRight: `4px solid ${COLORS.warning}`,
            padding: '16px 20px',
            margin: '20px 0',
          }}
        >
          <Text style={{ fontWeight: '700', color: COLORS.warning, fontSize: '15px', margin: '0 0 8px' }}>
            סיכום השיחה
          </Text>
          <Text style={{ margin: 0, fontSize: '14px', color: '#0d0f1a', lineHeight: '1.6' }}>{summary_hebrew}</Text>
        </Section>
      )}
      <Text style={{ ...mutedText, fontSize: '13px', marginTop: '20px' }}>
        אם יש שאלות או עדכונים, פנה/י דרך האפליקציה.
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
