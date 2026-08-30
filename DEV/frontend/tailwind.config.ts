import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  "extend": {
    "colors": {
      "on-error-container": "#93000a",
      "error-container": "#ffdad6",
      "on-error": "#ffffff",
      "on-secondary-fixed-variant": "#38485d",
      "inverse-primary": "#89ceff",
      "secondary": "#505f76",
      "on-surface": "#171c20",
      "secondary-fixed-dim": "#b7c8e1",
      "secondary-fixed": "#d3e4fe",
      "on-secondary-fixed": "#0b1c30",
      "secondary-container": "#d0e1fb",
      "surface-container-high": "#e4e8ee",
      "tertiary": "#8a5100",
      "on-secondary-container": "#54647a",
      "glass-bg": "rgba(255, 255, 255, 0.85)",
      "on-surface-variant": "#3e4850",
      "surface-variant": "#dee3e9",
      "surface-container-highest": "#dee3e9",
      "primary": "#006591",
      "background": "#f6faff",
      "on-primary-fixed": "#001e2f",
      "surface-dim": "#f3f4f6",
      "status-warning": "#f59e0b",
      "primary-container": "#0ea5e9",
      "surface-tint": "#006591",
      "on-background": "#171c20",
      "tertiary-fixed-dim": "#ffb86e",
      "on-secondary": "#ffffff",
      "on-primary-fixed-variant": "#004c6e",
      "surface": "#f6faff",
      "surface-bright": "#f6faff",
      "on-tertiary-fixed": "#2c1600",
      "surface-container-lowest": "#ffffff",
      "primary-fixed": "#c9e6ff",
      "surface-container-low": "#f0f4fa",
      "inverse-surface": "#2c3135",
      "outline-variant": "#bec8d2",
      "tertiary-container": "#de8712",
      "on-tertiary": "#ffffff",
      "tertiary-fixed": "#ffdcbd",
      "on-tertiary-container": "#4d2b00",
      "on-primary-container": "#003751",
      "on-primary": "#ffffff",
      "outline": "#6e7881",
      "primary-fixed-dim": "#89ceff",
      "on-tertiary-fixed-variant": "#693c00",
      "glass-border": "rgba(0, 0, 0, 0.05)",
      "inverse-on-surface": "#edf1f7",
      "status-error": "#ef4444",
      "surface-container": "#eaeef4",
      "status-success": "#10b981",
      "error": "#ba1a1a"
    },
    "borderRadius": {
      "DEFAULT": "0.25rem",
      "lg": "0.5rem",
      "xl": "0.75rem",
      "full": "9999px"
    },
    "spacing": {
      "header": "60px",
      "container-padding": "1rem",
      "unit": "4px",
      "gutter": "16px",
      "margin-page": "24px",
      "sidebar": "260px"
    },
    "fontFamily": {
      "body-md": [
        "Inter"
      ],
      "headline-lg-mobile": [
        "Inter"
      ],
      "headline-md": [
        "Inter"
      ],
      "display-lg": [
        "Inter"
      ],
      "label-md": [
        "JetBrains Mono"
      ]
    },
    "fontSize": {
      "body-md": [
        "14px",
        {
          "lineHeight": "20px",
          "fontWeight": "400"
        }
      ],
      "headline-lg-mobile": [
        "28px",
        {
          "lineHeight": "36px",
          "fontWeight": "700"
        }
      ],
      "headline-md": [
        "24px",
        {
          "lineHeight": "32px",
          "letterSpacing": "-0.01em",
          "fontWeight": "600"
        }
      ],
      "display-lg": [
        "36px",
        {
          "lineHeight": "44px",
          "letterSpacing": "-0.02em",
          "fontWeight": "700"
        }
      ],
      "label-md": [
        "12px",
        {
          "lineHeight": "16px",
          "fontWeight": "500"
        }
      ]
    }
  }
},
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
};
export default config;
