import { Section, Text } from '@react-email/components';
import * as React from 'react';

interface EmailOtpBoxProps {
  code: string;
  expiryMinutes?: number;
}

export default function EmailOtpBox({ code, expiryMinutes = 10 }: EmailOtpBoxProps) {
  return (
    <Section
      style={{
        backgroundColor: '#eef2ff',
        borderRadius: '12px',
        padding: '24px',
        textAlign: 'center',
        margin: '24px 0',
      }}
    >
      <Text style={{ margin: '0 0 8px', fontSize: '13px', color: '#5a607a' }}>קוד האימות שלך</Text>
      <Text
        style={{
          fontSize: '40px',
          fontWeight: '700',
          color: '#4F46E5',
          letterSpacing: '10px',
          margin: '0',
        }}
      >
        {code}
      </Text>
      <Text style={{ margin: '8px 0 0', fontSize: '12px', color: '#9ba3bf' }}>
        הקוד תקף ל-{expiryMinutes} דקות
      </Text>
    </Section>
  );
}
