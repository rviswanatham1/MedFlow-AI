import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Animated, SafeAreaView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Button } from '../../components/ui';
import { useApp } from '../../context/AppContext';

export default function TriageResultScreen() {
  const router = useRouter();
  const { triageResult } = useApp();
  const fadeIn  = useRef(new Animated.Value(0)).current;
  const slideUp = useRef(new Animated.Value(24)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeIn,  { toValue: 1, duration: 700, useNativeDriver: true }),
      Animated.spring(slideUp, { toValue: 0, useNativeDriver: true, tension: 55, friction: 8 }),
    ]).start();
  }, []);

  if (!triageResult) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={Colors.teal} size="large" />
        <Text style={{ color: Colors.gray400, marginTop: Spacing.md }}>Loading…</Text>
      </SafeAreaView>
    );
  }

  const t = triageResult;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Check-In Complete</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Animated.View style={{ opacity: fadeIn, transform: [{ translateY: slideUp }], gap: Spacing.lg }}>

          {/* ── Hero: Wait time ─────────────────────────────────────────────── */}
          <GlassCard style={styles.heroCard}>
            {/* Animated pulse ring */}
            <View style={styles.pulseOuter}>
              <View style={styles.pulseMiddle}>
                <View style={styles.pulseInner}>
                  <MaterialCommunityIcons name="clock-time-four-outline" size={32} color={Colors.teal} />
                </View>
              </View>
            </View>

            <Text style={styles.heroLabel}>ESTIMATED WAIT</Text>
            <Text style={styles.heroWait}>
              {t.estimated_wait == null
                ? '—'
                : t.estimated_wait === 0
                ? 'Immediate'
                : `${t.estimated_wait} min`}
            </Text>

            <View style={styles.heroDivider} />

            <View style={styles.heroQueueRow}>
              <MaterialCommunityIcons name="account-multiple-outline" size={16} color={Colors.gray400} />
              <Text style={styles.heroQueueText}>
                You are <Text style={styles.heroQueueNum}>{t.queue_position ?? '—'}</Text> in the queue
              </Text>
            </View>
          </GlassCard>

          {/* ── Reassurance banner ──────────────────────────────────────────── */}
          <View style={styles.reassureBanner}>
            <MaterialCommunityIcons name="shield-check" size={20} color={Colors.teal} />
            <View style={{ flex: 1 }}>
              <Text style={styles.reassureTitle}>You're all checked in</Text>
              <Text style={styles.reassureText}>
                A nurse will review your information and come to you shortly. Please stay in the waiting area.
              </Text>
            </View>
          </View>

          {/* ── What to expect ──────────────────────────────────────────────── */}
          <GlassCard style={styles.expectCard}>
            <Text style={styles.expectHeader}>What happens next?</Text>
            {[
              { icon: 'account-check-outline', color: Colors.teal,  text: 'A clinician reviews your information' },
              { icon: 'stethoscope',           color: Colors.blue,  text: 'You\'ll be called when it\'s your turn' },
              { icon: 'file-check-outline',    color: Colors.amber, text: 'Your care plan will be shared with you after review' },
            ].map((step, i) => (
              <View key={i} style={styles.expectRow}>
                <View style={[styles.expectIconWrap, { backgroundColor: `${step.color}18` }]}>
                  <MaterialCommunityIcons name={step.icon as any} size={18} color={step.color} />
                </View>
                <Text style={styles.expectText}>{step.text}</Text>
              </View>
            ))}
          </GlassCard>

          {/* ── Buttons ─────────────────────────────────────────────────────── */}
          <Button
            label="Back to Home"
            onPress={() => router.replace('/patient/home')}
            variant="ghost"
            size="md"
            style={{ width: '100%' }}
          />

          <Text style={styles.legalNote}>
            AI triage is for operational routing only and does not constitute medical advice.
          </Text>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md,
    borderBottomWidth: 1, borderBottomColor: Colors.glassBorder,
  },
  backBtn:     { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll:      { padding: Spacing.lg, paddingBottom: Spacing.xxl },

  // Hero card
  heroCard: {
    alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xl,
    borderColor: `${Colors.teal}33`, borderWidth: 1.5,
  },
  pulseOuter: {
    width: 100, height: 100, borderRadius: 50,
    backgroundColor: `${Colors.teal}0C`,
    alignItems: 'center', justifyContent: 'center',
    marginBottom: Spacing.sm,
  },
  pulseMiddle: {
    width: 78, height: 78, borderRadius: 39,
    backgroundColor: `${Colors.teal}18`,
    alignItems: 'center', justifyContent: 'center',
  },
  pulseInner: {
    width: 58, height: 58, borderRadius: 29,
    backgroundColor: `${Colors.teal}28`,
    alignItems: 'center', justifyContent: 'center',
  },
  heroLabel: { color: Colors.teal, fontSize: 11, fontWeight: '800', letterSpacing: 1.5 },
  heroWait:  { color: Colors.white, fontSize: 48, fontWeight: '900', lineHeight: 56 },
  heroDivider: { width: 60, height: 1, backgroundColor: Colors.glassBorder, marginVertical: Spacing.xs },
  heroQueueRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  heroQueueText: { color: Colors.gray400, fontSize: 13 },
  heroQueueNum:  { color: Colors.teal, fontWeight: '800' },

  // Reassurance banner
  reassureBanner: {
    flexDirection: 'row', gap: Spacing.md, alignItems: 'flex-start',
    backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}30`,
    borderRadius: Radius.md, padding: Spacing.md,
  },
  reassureTitle: { color: Colors.teal, fontSize: 14, fontWeight: '700', marginBottom: 3 },
  reassureText:  { color: Colors.gray400, fontSize: 13, lineHeight: 19 },

  // What to expect
  expectCard:   { gap: Spacing.md },
  expectHeader: { color: Colors.white, fontSize: 15, fontWeight: '700', marginBottom: Spacing.xs },
  expectRow:    { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  expectIconWrap: {
    width: 38, height: 38, borderRadius: 19,
    alignItems: 'center', justifyContent: 'center',
  },
  expectText: { color: Colors.gray400, fontSize: 13, lineHeight: 19, flex: 1 },

  legalNote: {
    color: Colors.gray600, fontSize: 10, textAlign: 'center',
    lineHeight: 15, paddingHorizontal: Spacing.md,
  },
});
