/** @type {import('tailwindcss').Config} */
import tailwindcssAnimate from 'tailwindcss-animate';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],

  /*
   * Preflight is OFF, deliberately.
   *
   * nocturne.css already owns the reset (box-sizing, html/body, margins) and
   * it does subtle things Tailwind's reset would clobber — notably
   * `html { overflow-x: clip }`, which is the only reason the full-bleed
   * Plate bands do not introduce a horizontal scrollbar. Two resets fighting
   * is how a working site goes dark mid-migration.
   *
   * Everything else (utilities, variants, the token bridge) is fully active,
   * so new work is utility-first while the hand-written layer keeps rendering.
   */
  corePlugins: { preflight: false },

  theme: {
    extend: {
      colors: {
        /* ── Token bridge ────────────────────────────────────────────────
           HSL triplets live in nocturne.css and are consumed here as
           hsl(var(--token)). Retheming is a variable swap, never a markup
           change — the same contract Bharath uses, retuned to near-black. */
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },

        /* The single accent. Used for state and emphasis, never decoration. */
        gold: {
          DEFAULT: 'hsl(var(--gold))',
          deep: 'hsl(var(--gold-deep))',
        },

        /* The near-black ladder, so utilities can reach it by name. */
        void: 'hsl(var(--void-h))',
        pit: 'hsl(var(--pit-h))',
        floor: 'hsl(var(--floor-h))',
        riser: 'hsl(var(--riser-h))',
      },

      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },

      fontFamily: {
        /* Mirrors nocturne.css's stacks so utility and hand-written type
           cannot drift apart. Tamil is listed inline: Inter has no Tamil
           glyphs, so the browser falls through per-codepoint. */
        display: ['"Archivo Black"', '"Inter"', 'system-ui', 'sans-serif'],
        sans: [
          '"Inter"',
          'system-ui',
          '-apple-system',
          '"Segoe UI"',
          '"Noto Sans Tamil"',
          '"Nirmala UI"',
          'sans-serif',
        ],
        mono: ['"JetBrains Mono"', 'ui-monospace', '"Cascadia Mono"', 'monospace'],
        tamil: ['"Noto Sans Tamil"', '"Nirmala UI"', 'sans-serif'],
        /* Figures only. Georgia ships on every target platform, so the
           high-contrast numeral costs 0 bytes — it never becomes a webfont
           request on the 2G path. */
        figure: ['Georgia', '"Times New Roman"', 'serif'],
      },

      fontSize: {
        /* 12px is the floor, not a choice. Established for multilingual and
           low-literacy users; Tailwind's text-xs (12px) is therefore the
           smallest step exposed, and text-[10px] etc. should never appear. */
        xs: ['12px', { lineHeight: '1.5' }],
      },

      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },

  plugins: [tailwindcssAnimate],
};
