import { Column, Row, Section } from '@react-email/components';
import * as React from 'react';

interface InfoRow {
  label: string;
  value: string;
}

interface EmailInfoBoxProps {
  color: string;
  rows: InfoRow[];
}

export default function EmailInfoBox({ color, rows }: EmailInfoBoxProps) {
  return (
    <Section
      style={{
        backgroundColor: '#f8f9fc',
        borderRadius: '10px',
        borderRight: `4px solid ${color}`,
        padding: '16px 20px',
        margin: '20px 0',
        direction: 'rtl',
      }}
    >
      {rows.map((row, i) => (
        <Row
          key={i}
          style={{
            borderBottom: i < rows.length - 1 ? '1px solid #f1f3f9' : 'none',
            padding: '8px 0',
          }}
        >
          <Column style={{ color: '#5a607a', fontSize: '14px' }}>{row.label}</Column>
          <Column
            style={{
              fontWeight: '600',
              color: '#0d0f1a',
              fontSize: '14px',
              textAlign: 'left',
            }}
          >
            {row.value}
          </Column>
        </Row>
      ))}
    </Section>
  );
}
