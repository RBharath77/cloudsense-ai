import './globals.css';
import type { ReactNode } from 'react';
import { ThemeProvider } from '../lib/theme';
import { I18nProvider } from '../lib/i18n';
import { CurrencyProvider } from '../lib/currency';

export const metadata = {
  title: 'CloudSense AI — Multi-Cloud FinOps & Carbon Intelligence',
  description: 'Autonomous multi-cloud cost intelligence, anomaly detection, carbon accounting, and FinOps automation across AWS, Azure, and GCP.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark" data-theme="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('cloudsense-theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  var theme = saved === 'light' || saved === 'dark' ? saved : (prefersDark ? 'dark' : 'light');
                  document.documentElement.classList.remove('light', 'dark');
                  document.documentElement.classList.add(theme);
                  document.documentElement.setAttribute('data-theme', theme);
                  document.documentElement.style.colorScheme = theme;
                } catch (e) {}
              })();
            `,
          }}
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen transition-colors duration-200">
        <ThemeProvider>
          <I18nProvider>
            <CurrencyProvider>
              {children}
            </CurrencyProvider>
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
