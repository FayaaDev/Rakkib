import { useState } from 'react'
import { I18nProvider } from './i18n/context'
import { useI18n } from './i18n/useI18n'
import { LanguageToggle } from './components/LanguageToggle'
import './App.css'

const installCommand = 'curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash'
const repoUrl = 'https://github.com/FayaaDev/Rakkib'

type Service = {
  name: string
  optional?: boolean
  icon: 'proxy' | 'cloud' | 'database' | 'table' | 'workflow' | 'mcp' | 'photos' | 'transfer' | 'claw' | 'hermes' | 'shield' | 'monitor' | 'docker'
}

const services: Service[] = [
  { name: 'Caddy', icon: 'proxy' },
  { name: 'Cloudflared', icon: 'cloud' },
  { name: 'PostgreSQL', icon: 'database' },
  { name: 'NocoDB', icon: 'table' },
  { name: 'Authentik', optional: true, icon: 'shield' },
  { name: 'Homepage', optional: true, icon: 'monitor' },
  { name: 'Uptime Kuma', optional: true, icon: 'monitor' },
  { name: 'Dockge', optional: true, icon: 'docker' },
  { name: 'n8n', optional: true, icon: 'workflow' },
  { name: 'DBHub', optional: true, icon: 'mcp' },
  { name: 'Immich', optional: true, icon: 'photos' },
  { name: 'transfer.sh', optional: true, icon: 'transfer' },
  { name: 'OpenClaw', optional: true, icon: 'claw' },
  { name: 'Hermes', optional: true, icon: 'hermes' },
]

function ServiceIcon({ icon }: { icon: Service['icon'] }) {
  if (icon === 'cloud') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M10 22h13a5 5 0 0 0 0-10 8 8 0 0 0-15-2 6 6 0 0 0 2 12Z" />
      </svg>
    )
  }

  if (icon === 'database') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <ellipse cx="16" cy="8" rx="9" ry="4" />
        <path d="M7 8v16c0 2 4 4 9 4s9-2 9-4V8" />
        <path d="M7 16c0 2 4 4 9 4s9-2 9-4" />
      </svg>
    )
  }

  if (icon === 'table') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect x="6" y="7" width="20" height="18" />
        <path d="M6 13h20M13 7v18M20 7v18" />
      </svg>
    )
  }

  if (icon === 'workflow') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <circle cx="8" cy="9" r="3" />
        <circle cx="24" cy="9" r="3" />
        <circle cx="16" cy="23" r="3" />
        <path d="M11 9h10M10 12l4 8M22 12l-4 8" />
      </svg>
    )
  }

  if (icon === 'mcp') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect x="6" y="6" width="8" height="8" />
        <rect x="18" y="6" width="8" height="8" />
        <rect x="12" y="18" width="8" height="8" />
        <path d="M14 10h4M10 14l4 4M22 14l-4 4" />
      </svg>
    )
  }

  if (icon === 'claw') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M8 25c4-3 5-8 5-17" />
        <path d="M16 25c2-4 3-9 2-18" />
        <path d="M23 25c-1-4-1-9 1-17" />
        <path d="M7 25h18" />
      </svg>
    )
  }

  if (icon === 'hermes') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 4l8 5v8c0 5-3 9-8 11-5-2-8-6-8-11V9l8-5Z" />
        <path d="M11 16h10" />
        <path d="M16 10v12" />
        <path d="M12 8c1 2 7 2 8 0" />
      </svg>
    )
  }

  if (icon === 'photos') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect x="5" y="8" width="22" height="17" rx="2" />
        <circle cx="12" cy="14" r="3" />
        <path d="M8 23l6-6 4 4 3-3 4 5" />
      </svg>
    )
  }

  if (icon === 'transfer') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 5v15" />
        <path d="M10 11l6-6 6 6" />
        <rect x="6" y="20" width="20" height="7" rx="2" />
        <path d="M21 24h1" />
      </svg>
    )
  }

  if (icon === 'shield') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 4l10 4v8c0 6-5 10-10 12-5-2-10-6-10-12V8l10-4Z" />
        <path d="M12 15l3 3 5-6" />
      </svg>
    )
  }

  if (icon === 'monitor') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect x="4" y="6" width="24" height="16" rx="2" />
        <path d="M12 26h8M16 22v4" />
      </svg>
    )
  }

  if (icon === 'docker') {
    return (
      <svg viewBox="0 0 32 32" aria-hidden="true">
        <rect x="8" y="4" width="6" height="6" rx="1" />
        <rect x="8" y="12" width="6" height="6" rx="1" />
        <rect x="18" y="12" width="6" height="6" rx="1" />
        <rect x="18" y="20" width="6" height="6" rx="1" />
        <path d="M14 7h4M14 15h4M20 15v5" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <rect x="6" y="8" width="20" height="16" />
      <path d="M10 13h7M10 18h12" />
    </svg>
  )
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.9 1.3 1.9 1.3 1 .1.7 2.9 3.2 2.1.1-.8.4-1.4.8-1.7-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.6.1-3.2 0 0 1-.3 3.3 1.2a11.3 11.3 0 0 1 6 0C17 6 18 6.3 18 6.3c.6 1.6.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.5.4.9 1.2.9 2.4v3.6c0 .3.2.7.8.6A12 12 0 0 0 12 .5Z" />
    </svg>
  )
}

function AppContent() {
  const { t, ts } = useI18n()
  const [copyLabel, setCopyLabel] = useState(t('copy'))

  async function copyInstallCommand() {
    await navigator.clipboard.writeText(installCommand)
    setCopyLabel(t('copied'))
    window.setTimeout(() => setCopyLabel(t('copy')), 1600)
  }

  return (
    <div className="shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label={t('brandLabel')}>
          <img className="brand-logo" src="/logo.png" alt="Rakkib logo" width="28" height="28" />
          [rakkib]
        </a>
        <div className="site-nav">
          <LanguageToggle />
          <a className="github-link" href={repoUrl} target="_blank" rel="noreferrer" aria-label="Rakkib on GitHub">
            <GitHubIcon />
            <span>{t('github')}</span>
          </a>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <img className="hero-logo" src="/logo-hero.png" alt="Rakkib" width="240" height="240" />
          <h1 id="hero-title">{t('heroTitle')}</h1>
          <p className="hero-text">
            {t('heroText')}
          </p>

          <div className="install-box" aria-label="Install command">
            <code>{installCommand}</code>
            <button type="button" onClick={copyInstallCommand} aria-live="polite">
              {copyLabel}
            </button>
          </div>
          <p className="install-note">
            {t('installNote')}
          </p>
        </section>

        <section className="services" aria-labelledby="services-title">
          <p className="section-label">{t('sectionLabel')}</p>
          <h2 id="services-title">{t('servicesTitle')}</h2>

          <div className="service-grid" role="list">
            {services.map((service) => (
              <article className="service-card" key={service.name} role="listitem">
                <div className="service-icon">
                  <ServiceIcon icon={service.icon} />
                </div>
                <div>
                  <h3>{service.name}</h3>
                  <p>{ts(service.name)}</p>
                </div>
                {service.optional ? <span className="badge">{t('optional')}</span> : null}
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

function App() {
  return (
    <I18nProvider>
      <AppContent />
    </I18nProvider>
  )
}

export default App
