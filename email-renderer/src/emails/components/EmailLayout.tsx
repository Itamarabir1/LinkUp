import {
  Body,
  Container,
  Head,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from '@react-email/components';
import * as React from 'react';

interface EmailLayoutProps {
  preview: string;
  headerColor: string;
  headerTitle: string;
  children: React.ReactNode;
}

export default function EmailLayout({
  preview,
  headerColor,
  headerTitle,
  children,
}: EmailLayoutProps) {
  return (
    <Html dir="rtl" lang="he">
      <Head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </Head>
      <Preview>{preview}</Preview>
      <Body style={styles.body}>
        <Container style={styles.container}>
          <Section style={{ ...styles.header, backgroundColor: headerColor }}>
            <Text style={styles.logoText}>LinkUp</Text>
            <Text style={styles.headerTitle}>{headerTitle}</Text>
          </Section>

          <Section style={styles.content}>{children}</Section>

          <Section style={styles.footer}>
            <Text style={styles.footerText}>© 2026 LinkUp · נוסעים יחד, חוסכים יחד</Text>
            <Text style={styles.footerLinks}>
              <Link href="https://linkup.co.il/unsubscribe" style={styles.footerLink}>
                הסר מרשימת תפוצה
              </Link>
              {' · '}
              <Link href="https://linkup.co.il/privacy" style={styles.footerLink}>
                מדיניות פרטיות
              </Link>
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

const styles: Record<string, React.CSSProperties> = {
  body: {
    backgroundColor: '#f8f9fc',
    fontFamily: "'Segoe UI', Arial, Helvetica, sans-serif",
    margin: 0,
    padding: '24px 0',
  },
  container: {
    maxWidth: '600px',
    margin: '0 auto',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  },
  header: {
    padding: '32px 40px',
    textAlign: 'center',
  },
  logoText: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: '18px',
    fontWeight: '700',
    margin: '0 0 8px',
    letterSpacing: '-0.5px',
  },
  headerTitle: {
    color: '#ffffff',
    fontSize: '24px',
    fontWeight: '700',
    margin: 0,
    letterSpacing: '-0.5px',
  },
  content: {
    backgroundColor: '#ffffff',
    padding: '32px 40px',
    direction: 'rtl' as const,
    textAlign: 'right' as const,
  },
  footer: {
    backgroundColor: '#f1f3f9',
    padding: '20px 40px',
    textAlign: 'center' as const,
  },
  footerText: {
    fontSize: '12px',
    color: '#9ba3bf',
    margin: '0 0 6px',
  },
  footerLinks: {
    fontSize: '12px',
    color: '#9ba3bf',
    margin: 0,
  },
  footerLink: {
    color: '#4F46E5',
    textDecoration: 'none',
  },
};
