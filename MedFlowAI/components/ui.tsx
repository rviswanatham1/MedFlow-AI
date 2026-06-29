import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { Colors, Radius, Spacing, Shadow } from '../constants/theme';

// ─── GlassCard ─────────────────────────────────────────────────────────────
interface GlassCardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  glow?: boolean;
}
export function GlassCard({ children, style, glow }: GlassCardProps) {
  return (
    <View
      style={[
        styles.glassCard,
        glow && styles.glassGlow,
        style,
      ]}
    >
      {children}
    </View>
  );
}

// ─── PrimaryButton ─────────────────────────────────────────────────────────
interface ButtonProps {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
  icon?: React.ReactNode;
}
export function Button({
  label,
  onPress,
  loading,
  disabled,
  variant = 'primary',
  size = 'md',
  style,
  icon,
}: ButtonProps) {
  const scale = useRef(new Animated.Value(1)).current;

  const handlePressIn = () =>
    Animated.spring(scale, { toValue: 0.96, useNativeDriver: true }).start();
  const handlePressOut = () =>
    Animated.spring(scale, { toValue: 1, useNativeDriver: true }).start();

  const btnStyle = {
    primary: styles.btnPrimary,
    outline: styles.btnOutline,
    ghost: styles.btnGhost,
    danger: styles.btnDanger,
  }[variant];

  const textStyle = {
    primary: styles.btnTextPrimary,
    outline: styles.btnTextOutline,
    ghost: styles.btnTextGhost,
    danger: styles.btnTextDanger,
  }[variant];

  const sizeStyle = {
    sm: styles.btnSm,
    md: styles.btnMd,
    lg: styles.btnLg,
  }[size];

  return (
    <TouchableOpacity
      activeOpacity={1}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={disabled || loading}
    >
      <Animated.View
        style={[
          styles.btnBase,
          btnStyle,
          sizeStyle,
          (disabled || loading) && styles.btnDisabled,
          style,
          { transform: [{ scale }] },
        ]}
      >
        {loading ? (
          <ActivityIndicator color={variant === 'primary' ? Colors.navy : Colors.teal} size="small" />
        ) : (
          <View style={styles.btnInner}>
            {icon && <View style={styles.btnIcon}>{icon}</View>}
            <Text style={[styles.btnTextBase, textStyle]}>{label}</Text>
          </View>
        )}
      </Animated.View>
    </TouchableOpacity>
  );
}

// ─── Badge ──────────────────────────────────────────────────────────────────
interface BadgeProps {
  label: string;
  color?: string;
  bg?: string;
}
export function Badge({ label, color = Colors.teal, bg }: BadgeProps) {
  return (
    <View style={[styles.badge, { backgroundColor: bg || `${color}22`, borderColor: `${color}44` }]}>
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

// ─── UrgencyIndicator ───────────────────────────────────────────────────────
interface UrgencyProps {
  level: 'low' | 'medium' | 'high' | 'critical';
}
export function UrgencyIndicator({ level }: UrgencyProps) {
  const URGENCY_MAP: Record<string, { label: string; color: string }> = {
    low:      { label: 'LOW',      color: Colors.urgencyLow      },
    medium:   { label: 'MEDIUM',   color: Colors.urgencyMedium   },
    moderate: { label: 'MEDIUM',   color: Colors.urgencyMedium   },
    high:     { label: 'HIGH',     color: Colors.urgencyHigh     },
    urgent:   { label: 'HIGH',     color: Colors.urgencyHigh     },
    critical: { label: 'CRITICAL', color: Colors.urgencyCritical },
    emergency:{ label: 'CRITICAL', color: Colors.urgencyCritical },
  };
  const config = URGENCY_MAP[String(level).toLowerCase()] ?? { label: String(level ?? 'UNKNOWN').toUpperCase(), color: Colors.urgencyMedium };

  return (
    <View style={[styles.urgencyBadge, { borderColor: config.color, backgroundColor: `${config.color}18` }]}>
      <View style={[styles.urgencyDot, { backgroundColor: config.color }]} />
      <Text style={[styles.urgencyText, { color: config.color }]}>{config.label}</Text>
    </View>
  );
}

// ─── ConfidenceBar ──────────────────────────────────────────────────────────
interface ConfidenceBarProps {
  score: number; // 0-100
  label?: string;
}
export function ConfidenceBar({ score, label }: ConfidenceBarProps) {
  const color = score >= 80 ? Colors.green : score >= 60 ? Colors.amber : Colors.red;
  return (
    <View style={styles.confidenceContainer}>
      {label && <Text style={styles.confidenceLabel}>{label}</Text>}
      <View style={styles.confidenceTrack}>
        <View style={[styles.confidenceFill, { width: `${score}%` as any, backgroundColor: color }]} />
      </View>
      <Text style={[styles.confidenceScore, { color }]}>{score}%</Text>
    </View>
  );
}

// ─── PulseOrb ───────────────────────────────────────────────────────────────
export function PulseOrb({ size = 60, color = Colors.teal }: { size?: number; color?: string }) {
  const pulse = useRef(new Animated.Value(1)).current;
  const opacity = useRef(new Animated.Value(0.6)).current;

  useEffect(() => {
    Animated.loop(
      Animated.parallel([
        Animated.sequence([
          Animated.timing(pulse, { toValue: 1.3, duration: 1000, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1, duration: 1000, useNativeDriver: true }),
        ]),
        Animated.sequence([
          Animated.timing(opacity, { toValue: 0.1, duration: 1000, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0.6, duration: 1000, useNativeDriver: true }),
        ]),
      ])
    ).start();
  }, []);

  return (
    <View style={{ width: size * 1.4, height: size * 1.4, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View
        style={{
          position: 'absolute',
          width: size * 1.4,
          height: size * 1.4,
          borderRadius: size,
          backgroundColor: color,
          opacity,
          transform: [{ scale: pulse }],
        }}
      />
      <View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      />
    </View>
  );
}

// ─── SectionHeader ──────────────────────────────────────────────────────────
interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: { label: string; onPress: () => void };
}
export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <View>
        <Text style={styles.sectionTitle}>{title}</Text>
        {subtitle && <Text style={styles.sectionSubtitle}>{subtitle}</Text>}
      </View>
      {action && (
        <TouchableOpacity onPress={action.onPress}>
          <Text style={styles.sectionAction}>{action.label}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─── Divider ────────────────────────────────────────────────────────────────
export function Divider({ style }: { style?: ViewStyle }) {
  return <View style={[styles.divider, style]} />;
}

const styles = StyleSheet.create({
  glassCard: {
    backgroundColor: Colors.glass,
    borderWidth: 1,
    borderColor: Colors.glassBorder,
    borderRadius: Radius.lg,
    padding: Spacing.md,
  },
  glassGlow: {
    borderColor: `${Colors.teal}44`,
    shadowColor: Colors.teal,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 8,
  },
  btnBase: {
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnPrimary: {
    backgroundColor: Colors.teal,
  },
  btnOutline: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: Colors.teal,
  },
  btnGhost: {
    backgroundColor: Colors.tealDim,
  },
  btnDanger: {
    backgroundColor: Colors.red,
  },
  btnSm: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2, minHeight: 36 },
  btnMd: { paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm + 4, minHeight: 48 },
  btnLg: { paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, minHeight: 56 },
  btnDisabled: { opacity: 0.5 },
  btnInner: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  btnIcon: { marginRight: 4 },
  btnTextBase: { fontWeight: '700', letterSpacing: 0.3 },
  btnTextPrimary: { color: Colors.navy, fontSize: 15 },
  btnTextOutline: { color: Colors.teal, fontSize: 15 },
  btnTextGhost: { color: Colors.teal, fontSize: 15 },
  btnTextDanger: { color: Colors.white, fontSize: 15 },
  badge: {
    borderWidth: 1,
    borderRadius: Radius.full,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  badgeText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  urgencyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: Radius.full,
    paddingHorizontal: 12,
    paddingVertical: 4,
    gap: 6,
  },
  urgencyDot: { width: 6, height: 6, borderRadius: 3 },
  urgencyText: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  confidenceContainer: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  confidenceLabel: { color: Colors.gray400, fontSize: 12, width: 80 },
  confidenceTrack: {
    flex: 1,
    height: 6,
    backgroundColor: Colors.navyLight,
    borderRadius: Radius.full,
    overflow: 'hidden',
  },
  confidenceFill: { height: '100%', borderRadius: Radius.full },
  confidenceScore: { fontSize: 12, fontWeight: '700', width: 36, textAlign: 'right' },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: Spacing.md,
  },
  sectionTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  sectionSubtitle: { color: Colors.gray400, fontSize: 13, marginTop: 2 },
  sectionAction: { color: Colors.teal, fontSize: 13, fontWeight: '600' },
  divider: { height: 1, backgroundColor: Colors.glassBorder, marginVertical: Spacing.md },
});
