import { useEffect, useState } from 'react'
import { useAuth } from './useAuth'
import { useTheme } from './useTheme'

interface BrandTheme {
  theme_id: string
  id?: string
  name?: string
  logo_text?: string
  accent?: string
  accent_hover?: string
  accent_muted?: string
  accent_light?: string
  accent_gradient?: string
  accent_glow?: string
  brand_clay?: string
  dark?: Record<string, string>
  light?: Record<string, string>
}

const VAR_MAP: Record<string, string> = {
  bg_primary: '--bg-primary',
  bg_sidebar: '--bg-sidebar',
  bg_card: '--bg-card',
  bg_input: '--bg-input',
  bg_hover: '--bg-hover',
  text_primary: '--text-primary',
  text_secondary: '--text-secondary',
  text_muted: '--text-muted',
  border: '--border',
}

export function useBrandTheme() {
  const { user } = useAuth()
  const { theme } = useTheme()  // 'light' | 'dark'
  const [brand, setBrand] = useState<BrandTheme | null>(null)

  // Fetch theme on login
  useEffect(() => {
    if (!user) return
    const token = localStorage.getItem('neura_token')
    if (!token) return

    fetch('/api/theme', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.theme_id !== 'default') {
          setBrand(data)
        }
      })
      .catch(() => {})  // silent fail — use defaults
  }, [user])

  // Apply CSS variables when brand or light/dark changes
  useEffect(() => {
    const root = document.documentElement

    if (!brand || brand.theme_id === 'default') {
      // Remove any brand overrides
      root.removeAttribute('data-brand')
      return
    }

    root.setAttribute('data-brand', brand.id || brand.theme_id)

    // Apply accent colors (same for light and dark)
    if (brand.accent) {
      root.style.setProperty('--accent', brand.accent)
      root.style.setProperty('--border-focus', brand.accent)
    }
    if (brand.accent_hover) root.style.setProperty('--accent-hover', brand.accent_hover)
    if (brand.accent_muted) root.style.setProperty('--accent-muted', brand.accent_muted)
    if (brand.accent_light) root.style.setProperty('--accent-light', brand.accent_light)
    if (brand.accent_gradient) root.style.setProperty('--accent-gradient', brand.accent_gradient)
    if (brand.accent_glow) root.style.setProperty('--accent-glow', brand.accent_glow)
    if (brand.brand_clay) root.style.setProperty('--brand-clay', brand.brand_clay)

    // Apply theme-specific colors (bg, text, border)
    const modeColors = theme === 'light' ? brand.light : brand.dark
    if (modeColors) {
      for (const [key, cssVar] of Object.entries(VAR_MAP)) {
        if (modeColors[key]) {
          root.style.setProperty(cssVar, modeColors[key])
        }
      }
    }

    // Cleanup: remove inline styles when brand changes or unmounts
    return () => {
      const allVars = [
        '--accent', '--accent-hover', '--accent-muted', '--accent-light',
        '--accent-gradient', '--accent-glow', '--brand-clay', '--border-focus',
        ...Object.values(VAR_MAP),
      ]
      allVars.forEach((v) => root.style.removeProperty(v))
      root.removeAttribute('data-brand')
    }
  }, [brand, theme])

  return {
    brandName: brand?.logo_text || brand?.name || 'Neura',
    brandId: brand?.id || 'default',
    isBranded: !!brand && brand.theme_id !== 'default',
  }
}
