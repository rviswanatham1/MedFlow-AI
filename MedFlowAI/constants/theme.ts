export const Colors = {
  // Core palette
  navy: '#0A1628',
  navyMid: '#112240',
  navyLight: '#1D3461',
  teal: '#00C2A8',
  tealLight: '#33D9C3',
  tealDim: 'rgba(0, 194, 168, 0.15)',
  tealDim2: 'rgba(0, 194, 168, 0.08)',

  // Accents
  amber: '#F59E0B',
  red: '#EF4444',
  green: '#10B981',
  blue: '#3B82F6',

  // Neutrals
  white: '#FFFFFF',
  offWhite: '#F8FAFC',
  gray100: '#F1F5F9',
  gray200: '#E2E8F0',
  gray400: '#94A3B8',
  gray600: '#475569',
  gray800: '#1E293B',

  // Urgency levels
  urgencyLow: '#10B981',
  urgencyMedium: '#F59E0B',
  urgencyHigh: '#EF4444',
  urgencyCritical: '#DC2626',

  // Glassmorphism
  glass: 'rgba(255,255,255,0.06)',
  glassBorder: 'rgba(255,255,255,0.12)',
};

export const FontFamily = {
  display: 'System', // Will use native bold - pretend this is a display font
  body: 'System',
  mono: 'Courier New',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const Radius = {
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  full: 999,
};

export const Shadow = {
  teal: {
    shadowColor: '#00C2A8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
};
