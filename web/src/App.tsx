import { useState } from 'react'
import './App.css'

const installCommand = 'curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash'
const repoUrl = 'https://github.com/FayaaDev/Rakkib'

type Service = {
  name: string
  description: string
  optional?: boolean
  icon: 'proxy' | 'cloud' | 'database' | 'table' | 'workflow' | 'mcp' | 'claw'
}

const services: Service[] = [
  {
    name: 'Caddy',
    description: 'Web server',
    icon: 'proxy',
  },
  {
    name: 'Cloudflared',
    description: 'Secure tunnel',
    icon: 'cloud',
  },
  {
    name: 'PostgreSQL',
    description: 'Database',
    icon: 'database',
  },
  {
    name: 'NocoDB',
    description: 'No-code data UI',
    icon: 'table',
  },
  {
    name: 'n8n',
    description: 'Automation',
    optional: true,
    icon: 'workflow',
  },
  {
    name: 'DBHub',
    description: 'Database MCP',
    optional: true,
    icon: 'mcp',
  },
  {
    name: 'OpenClaw',
    description: 'AI control UI',
    optional: true,
    icon: 'claw',
  },
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

function App() {
  const [copyLabel, setCopyLabel] = useState('copy')

  async function copyInstallCommand() {
    await navigator.clipboard.writeText(installCommand)
    setCopyLabel('copied')
    window.setTimeout(() => setCopyLabel('copy'), 1600)
  }

  return (
    <div className="shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Rakkib home">
          [rakkib]
        </a>
        <a className="github-link" href={repoUrl} target="_blank" rel="noreferrer" aria-label="Rakkib on GitHub">
          <GitHubIcon />
          <span>GitHub</span>
        </a>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <p className="eyebrow">personal server kit</p>
          <h1 id="hero-title">Your own server, installed by an AI agent.</h1>
          <p className="hero-text">
            Rakkib turns a fresh machine into a clean self-hosted stack for apps, databases, automation, and secure access.
          </p>

          <div className="install-box" aria-label="Install command">
            <code>{installCommand}</code>
            <button type="button" onClick={copyInstallCommand} aria-live="polite">
              {copyLabel}
            </button>
          </div>
          <p className="install-note">
            Paste the above command into your terminal. Rakkib detects your AI coding agent
            (Claude Code, Codex, or OpenCode), checks your system, opens an agent session, and
            loads the setup prompt automatically. You just answer the questions.
          </p>
        </section>

        <section className="services" aria-labelledby="services-title">
          <p className="section-label">installed services</p>
          <h2 id="services-title">Core stack included. Optional tools when you want them.</h2>

          <div className="service-grid" role="list">
            {services.map((service) => (
              <article className="service-card" key={service.name} role="listitem">
                <div className="service-icon">
                  <ServiceIcon icon={service.icon} />
                </div>
                <div>
                  <h3>{service.name}</h3>
                  <p>{service.description}</p>
                </div>
                {service.optional ? <span className="badge">optional</span> : null}
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
