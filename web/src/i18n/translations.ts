export type Locale = 'en' | 'ar'

export const translations = {
  en: {
    metaTitle: 'Rakkib - Agent-Driven Homeserver Setup',
    metaDescription: 'Rakkib turns a fresh machine into a self-hosted server stack with one guided install command.',
    brandLabel: 'Rakkib home',
    heroTitle: 'Your own server, installed by an AI agent.',
    heroText:
      'Rakkib transforms a fresh machine into a polished self-hosted stack for apps, data, automation, photos, and secure access.',
    copy: 'Copy',
    copied: 'Copied!',
    installNote:
      'One command. Guided setup. Rakkib finds your agent, prepares the machine, and walks you into a secure self-hosted stack.',
    sectionLabel: 'Installed services',
    servicesTitle: 'Core stack included. Optional tools when you want them.',
    optional: 'Optional',
    github: 'GitHub',
    services: {
      Caddy: 'Web server',
      Cloudflared: 'Secure tunnel',
      PostgreSQL: 'Database',
      NocoDB: 'No-code data UI',
      Authentik: 'SSO & auth proxy',
      Homepage: 'Service dashboard',
      'Uptime Kuma': 'Uptime monitoring',
      Dockge: 'Docker Compose UI',
      n8n: 'Automation',
      DBHub: 'Database MCP',
      Immich: 'Photo library',
      'transfer.sh': 'Public file sharing',
      OpenClaw: 'AI control UI',
      Hermes: 'AI agent dashboard',
    },
  },
  ar: {
    metaTitle: 'رَكِّب — إعداد خادم بوكيل ذكاء اصطناعي',
    metaDescription: 'رَكِّب يحوّل جهازًا جديدًا إلى حزمة استضافة ذاتية بأمر تثبيت واحد مُوجّه.',
    brandLabel: 'صفحة رَكِّب الرئيسية',
    heroTitle: 'خادمك الخاص، يُثبّته وكيل ذكاء اصطناعي.',
    heroText:
      'رَكِّب يحوّل جهازًا جديدًا إلى حزمة استضافة ذاتية متكاملة للتطبيقات والبيانات والأتمتة والصور والوصول الآمن.',
    copy: 'نسخ',
    copied: 'تم النسخ!',
    installNote:
      'أمر واحد. إعداد موجّه. رَكِّب يجد وكيلك ويُعِدّ الجهاز ويقودك إلى حزمة استضافة ذاتية آمنة.',
    sectionLabel: 'الخدمات المُثبّتة',
    servicesTitle: 'حزمة أساسية مشمولة. أدوات اختيارية متى أردت.',
    optional: 'اختياري',
    github: 'جيت‌هب',
    services: {
      Caddy: 'خادم ويب',
      Cloudflared: 'نفق آمن',
      PostgreSQL: 'قاعدة بيانات',
      NocoDB: 'واجهة بيانات بلا كود',
      Authentik: 'تسجيل دخول موحّد',
      Homepage: 'لوحة الخدمات',
      'Uptime Kuma': 'مراقبة التشغيل',
      Dockge: 'واجهة Docker Compose',
      n8n: 'أتمتة',
      DBHub: 'قاعدة بيانات MCP',
      Immich: 'مكتبة صور',
      'transfer.sh': 'مشاركة ملفات عامة',
      OpenClaw: 'واجهة تحكم ذكاء اصطناعي',
      Hermes: 'لوحة وكيل ذكاء اصطناعي',
    },
  },
} as const

export type TranslationKey = keyof typeof translations.en