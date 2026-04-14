import { Button } from '@react-email/components';
import * as React from 'react';

interface EmailButtonProps {
  href: string;
  color: string;
  children: React.ReactNode;
}

export default function EmailButton({ href, color, children }: EmailButtonProps) {
  return (
    <div style={{ textAlign: 'center', marginTop: '28px' }}>
      <Button
        href={href}
        style={{
          backgroundColor: color,
          color: '#ffffff',
          padding: '14px 32px',
          borderRadius: '10px',
          fontWeight: '700',
          fontSize: '15px',
          textDecoration: 'none',
          letterSpacing: '-0.3px',
          display: 'inline-block',
        }}
      >
        {children}
      </Button>
    </div>
  );
}
