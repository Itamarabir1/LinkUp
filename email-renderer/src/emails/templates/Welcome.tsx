import { Column, Row, Section, Text } from '@react-email/components';
import * as React from 'react';
import EmailButton from '../components/EmailButton';
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
  dashboard_url?: string;
}

const features = [
  { icon: '🔍', title: 'חפש נסיעות', desc: 'מצא נסיעות קרובות שמתאימות לך' },
  { icon: '🚘', title: 'הצע נסיעה', desc: 'הצע נסיעה ועזור לאחרים להגיע ליעד' },
  { icon: '💬', title: 'תקשר', desc: "פנה לנהג/נוסע דרך הצ'אט" },
];

export default function Welcome({ user_name, dashboard_url = 'https://linkup.co.il' }: Props) {
  return (
    <EmailLayout
      preview={`ברוכים הבאים ל-Linkup, ${user_name || ''}!`}
      headerColor={COLORS.primary}
      headerTitle="ברוכים הבאים ל-Linkup! 🚗"
    >
      <Text style={bodyText}>
        היי <strong>{user_name}</strong>,
      </Text>
      <Text style={mutedText}>
        אנחנו שמחים שהצטרפת לקהילת Linkup — המקום לתאם נסיעות משותפות ולחסוך ביחד.
      </Text>
      <Section style={{ margin: '20px 0' }}>
        {features.map((f, i) => (
          <Row
            key={i}
            style={{
              borderBottom: i < features.length - 1 ? '1px solid #f1f3f9' : 'none',
              padding: '10px 0',
            }}
          >
            <Column style={{ width: '32px', fontSize: '20px' }}>{f.icon}</Column>
            <Column>
              <strong style={{ color: '#0d0f1a' }}>{f.title}</strong>
              <span style={{ color: '#5a607a', fontSize: '14px' }}> — {f.desc}</span>
            </Column>
          </Row>
        ))}
      </Section>
      <EmailButton href={dashboard_url} color={COLORS.primary}>
        התחל עכשיו
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
