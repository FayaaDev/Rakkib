import { useI18n } from '../i18n/useI18n'

export function LanguageToggle() {
  const { locale, setLocale } = useI18n()

  return (
    <button
      type="button"
      className="lang-toggle"
      onClick={() => setLocale(locale === 'en' ? 'ar' : 'en')}
      aria-label={locale === 'en' ? 'التبديل إلى العربية' : 'Switch to English'}
    >
      {locale === 'en' ? 'عربي' : 'EN'}
    </button>
  )
}
