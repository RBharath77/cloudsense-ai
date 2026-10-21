'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

export type CurrencyCode = 'USD' | 'INR' | 'EUR' | 'GBP' | 'JPY' | 'CAD' | 'AUD' | 'AED';

export interface CurrencyMeta {
  code: CurrencyCode;
  symbol: string;
  name: string;
  rateToUSD: number; // 1 USD = rateToUSD
  flag: string;
}

export const CURRENCIES: Record<CurrencyCode, CurrencyMeta> = {
  USD: { code: 'USD', symbol: '$', name: 'US Dollar', rateToUSD: 1.0, flag: '🇺🇸' },
  INR: { code: 'INR', symbol: '₹', name: 'Indian Rupee', rateToUSD: 83.5, flag: '🇮🇳' },
  EUR: { code: 'EUR', symbol: '€', name: 'Euro', rateToUSD: 0.92, flag: '🇪🇺' },
  GBP: { code: 'GBP', symbol: '£', name: 'British Pound', rateToUSD: 0.78, flag: '🇬🇧' },
  JPY: { code: 'JPY', symbol: '¥', name: 'Japanese Yen', rateToUSD: 152.0, flag: '🇯🇵' },
  CAD: { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar', rateToUSD: 1.36, flag: '🇨🇦' },
  AUD: { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', rateToUSD: 1.50, flag: '🇦🇺' },
  AED: { code: 'AED', symbol: 'AED', name: 'UAE Dirham', rateToUSD: 3.67, flag: '🇦🇪' },
};

interface CurrencyContextType {
  currency: CurrencyCode;
  setCurrency: (code: CurrencyCode) => void;
  formatCurrency: (amountInUSD: number, options?: { decimals?: number }) => string;
  currencies: CurrencyMeta[];
  detectedCurrency: CurrencyCode;
}

const CurrencyContext = createContext<CurrencyContextType>({
  currency: 'USD',
  setCurrency: () => {},
  formatCurrency: (amt) => `$${amt.toFixed(2)}`,
  currencies: Object.values(CURRENCIES),
  detectedCurrency: 'USD',
});

export function predictCurrencyFromEnvironment(): CurrencyCode {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    const tzLower = tz.toLowerCase();

    if (
      tzLower.includes('kolkata') ||
      tzLower.includes('calcutta') ||
      tzLower.includes('colombo') ||
      tzLower.includes('india')
    ) {
      return 'INR';
    }
    if (tzLower.includes('london') || tzLower.includes('britain') || tzLower.includes('belfast')) {
      return 'GBP';
    }
    if (
      tzLower.includes('paris') ||
      tzLower.includes('berlin') ||
      tzLower.includes('madrid') ||
      tzLower.includes('rome') ||
      tzLower.includes('amsterdam') ||
      tzLower.includes('brussels') ||
      tzLower.includes('europe')
    ) {
      return 'EUR';
    }
    if (tzLower.includes('tokyo') || tzLower.includes('japan')) {
      return 'JPY';
    }
    if (tzLower.includes('toronto') || tzLower.includes('vancouver') || tzLower.includes('montreal')) {
      return 'CAD';
    }
    if (tzLower.includes('sydney') || tzLower.includes('melbourne') || tzLower.includes('brisbane')) {
      return 'AUD';
    }
    if (tzLower.includes('dubai') || tzLower.includes('emirates')) {
      return 'AED';
    }
  } catch {}
  return 'USD';
}

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<CurrencyCode>('USD');
  const [detectedCurrency, setDetectedCurrency] = useState<CurrencyCode>('USD');

  useEffect(() => {
    try {
      const predicted = predictCurrencyFromEnvironment();
      setDetectedCurrency(predicted);

      const saved = localStorage.getItem('cloudsense_currency') as CurrencyCode;
      if (saved && CURRENCIES[saved]) {
        setCurrencyState(saved);
      } else {
        // Auto-adopt predicted currency if not explicitly overridden
        setCurrencyState(predicted);
      }
    } catch {}
  }, []);

  const setCurrency = (code: CurrencyCode) => {
    setCurrencyState(code);
    try {
      localStorage.setItem('cloudsense_currency', code);
    } catch {}
  };

  const formatCurrency = (amountInUSD: number, options?: { decimals?: number }): string => {
    if (typeof amountInUSD !== 'number' || isNaN(amountInUSD)) return '$0.00';
    const meta = CURRENCIES[currency] || CURRENCIES.USD;
    const converted = amountInUSD * meta.rateToUSD;
    const dec = options?.decimals !== undefined ? options.decimals : meta.code === 'JPY' ? 0 : 2;

    const formattedNumber = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    }).format(converted);

    return `${meta.symbol} ${formattedNumber}`;
  };

  return (
    <CurrencyContext.Provider
      value={{
        currency,
        setCurrency,
        formatCurrency,
        currencies: Object.values(CURRENCIES),
        detectedCurrency,
      }}
    >
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
