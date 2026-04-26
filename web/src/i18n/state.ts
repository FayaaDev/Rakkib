import { createContext } from 'react'
import type { Locale, TranslationKey } from './translations'

export type I18nContextValue = {
  locale: Locale
  dir: 'ltr' | 'rtl'
  t: (key: TranslationKey) => string
  ts: (key: string) => string
  setLocale: (locale: Locale) => void
}

export const I18nContext = createContext<I18nContextValue | null>(null)
