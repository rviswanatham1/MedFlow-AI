import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  SafeAreaView, ActivityIndicator, Share, RefreshControl, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api, CarePlan } from '../../services/api';

const URGENCY_COLOR: Record<string, string> = {
  STAT:    Colors.red,
  ASAP:    Colors.amber,
  Routine: Colors.green,
};

const ROUTE_COLOR: Record<string, string> = {
  PO:      Colors.teal,
  IV:      Colors.red,
  IM:      Colors.amber,
  SQ:      Colors.blue,
  Topical: Colors.green,
  Inhaled: Colors.blue,
};

// ── Section divider ──────────────────────────────────────────────────────────
function SectionLabel({ title }: { title: string }) {
  return (
    <View style={styles.sectionLabel}>
      <View style={styles.sectionLine} />
      <Text style={styles.sectionLabelText}>{title}</Text>
      <View style={styles.sectionLine} />
    </View>
  );
}

// ── Main screen ──────────────────────────────────────────────────────────────
export default function ApprovedReportScreen() {
  const router   = useRouter();
  const { patientId, profile } = useApp();

  const [plan, setPlan]           = useState<CarePlan | null>(null);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sharing, setSharing]     = useState(false);

  const fetchPlan = useCallback(async () => {
    try {
      const data = await api.getCarePlan(patientId, 'patient');
      setPlan(data);
    } catch {
      setPlan({ exists: false });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [patientId]);

  useEffect(() => { fetchPlan(); }, [fetchPlan]);
  const onRefresh = () => { setRefreshing(true); fetchPlan(); };

  // ── Plain-text export ──────────────────────────────────────────────────────
  const buildPlainText = (): string => {
    if (!plan?.exists) return 'Care plan not yet available.';
    const name = profile?.name ?? patientId;
    const lines: string[] = [
      '═══════════════════════════════════════',
      '       MEDFLOW AI — YOUR CARE PLAN',
      '═══════════════════════════════════════',
      '',
      `Patient:   ${name}`,
      `ID:        ${patientId}`,
      `Approved:  ${plan.approved_at ? new Date(plan.approved_at).toLocaleString() : '—'}`,
      `Doctor:    ${plan.doctor_id ?? '—'}`,
      '',
    ];

    if (plan.labs?.length) {
      lines.push('───────────────────────────────────────');
      lines.push('  LABS ORDERED');
      lines.push('───────────────────────────────────────');
      plan.labs.forEach(l => {
        lines.push(`  [${l.urgency}] ${l.name}`);
        lines.push(`         Timing: ${l.timing}`);
        if (l.notes) lines.push(`         Notes:  ${l.notes}`);
      });
      lines.push('');
    }

    if (plan.medications?.length) {
      lines.push('───────────────────────────────────────');
      lines.push('  MEDICATIONS');
      lines.push('───────────────────────────────────────');
      plan.medications.forEach(m => {
        lines.push(`  ${m.name} — ${m.dose}`);
        lines.push(`         ${m.frequency} | ${m.route}${m.duration ? ` | ${m.duration}` : ''}`);
        if (m.notes) lines.push(`         ${m.notes}`);
      });
      lines.push('');
    }

    if (plan.instructions) {
      lines.push('───────────────────────────────────────');
      lines.push('  INSTRUCTIONS');
      lines.push('───────────────────────────────────────');
      lines.push(plan.instructions);
      lines.push('');
    }

    if (plan.follow_up) {
      lines.push('───────────────────────────────────────');
      lines.push('  FOLLOW-UP');
      lines.push('───────────────────────────────────────');
      lines.push(plan.follow_up);
      lines.push('');
    }

    if (plan.diet) {
      lines.push('───────────────────────────────────────');
      lines.push('  DIET PLAN');
      lines.push('───────────────────────────────────────');
      lines.push(plan.diet);
      lines.push('');
    }

    if (plan.activity) {
      lines.push('───────────────────────────────────────');
      lines.push('  ACTIVITY GUIDELINES');
      lines.push('───────────────────────────────────────');
      lines.push(plan.activity);
      lines.push('');
    }

    lines.push('═══════════════════════════════════════');
    lines.push('This care plan was reviewed and approved by a licensed clinician.');
    lines.push(`Generated: ${new Date().toLocaleString()}`);
    lines.push('═══════════════════════════════════════');
    return lines.join('\n');
  };

  const handleShare = async () => {
    setSharing(true);
    try {
      await Share.share({
        message: buildPlainText(),
        title: `MedflowAI Care Plan — ${profile?.name ?? patientId}`,
      });
    } catch {
      Alert.alert('Share failed', 'Could not open the share sheet.');
    } finally {
      setSharing(false);
    }
  };

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={Colors.teal} size="large" />
        <Text style={{ color: Colors.gray400, marginTop: Spacing.md }}>Loading care plan…</Text>
      </SafeAreaView>
    );
  }

  // ── Pending ────────────────────────────────────────────────────────────────
  if (!plan?.exists) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
            <Ionicons name="arrow-back" size={22} color={Colors.white} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>My Care Plan</Text>
          <View style={{ width: 40 }} />
        </View>
        <ScrollView
          contentContainerStyle={styles.pendingWrap}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.teal} />}
        >
          <View style={styles.pendingClockWrap}>
            <MaterialCommunityIcons name="clock-outline" size={52} color={Colors.amber} />
          </View>
          <Text style={styles.pendingTitle}>Care Plan Being Prepared</Text>
          <Text style={styles.pendingBody}>
            Your doctor is reviewing your triage and will finalize your personalized care plan shortly.
          </Text>
          <GlassCard style={{ width: '100%' }}>
            <View style={{ flexDirection: 'row', gap: Spacing.sm, alignItems: 'flex-start' }}>
              <MaterialCommunityIcons name="shield-check-outline" size={18} color={Colors.teal} />
              <Text style={styles.pendingInfoText}>
                Your care plan includes labs, medications, and instructions tailored to your condition — approved by your clinician.
              </Text>
            </View>
          </GlassCard>
          <TouchableOpacity style={styles.refreshBtn} onPress={onRefresh}>
            <MaterialCommunityIcons name="refresh" size={16} color={Colors.teal} />
            <Text style={styles.refreshBtnText}>Pull down or tap to refresh</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <View style={{ alignItems: 'center' }}>
          <Text style={styles.headerTitle}>My Care Plan</Text>
          <Text style={styles.headerSub}>Approved by your doctor</Text>
        </View>
        <TouchableOpacity style={styles.iconBtn} onPress={handleShare} disabled={sharing}>
          {sharing
            ? <ActivityIndicator size="small" color={Colors.teal} />
            : <MaterialCommunityIcons name="share-outline" size={22} color={Colors.teal} />}
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.teal} />}
      >
        {/* ── Approval stamp ──────────────────────────────────────────────── */}
        <View style={styles.approvalHero}>
          <View style={styles.approvalCheck}>
            <MaterialCommunityIcons name="check-bold" size={28} color={Colors.navy} />
          </View>
          <View style={{ alignItems: 'center', gap: 4 }}>
            <Text style={styles.approvalTitle}>Care Plan Approved</Text>
            <Text style={styles.approvalSub}>
              By {plan.doctor_id ?? 'Your Doctor'}
              {plan.approved_at ? `  ·  ${new Date(plan.approved_at).toLocaleDateString()}` : ''}
            </Text>
          </View>
        </View>

        {/* ── Patient card ─────────────────────────────────────────────────── */}
        <GlassCard style={styles.patientCard}>
          <View style={styles.patientRow}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{profile?.initials ?? (profile?.name?.[0] ?? '?')}</Text>
            </View>
            <View style={{ flex: 1, gap: 3 }}>
              <Text style={styles.patientName}>{profile?.name ?? patientId}</Text>
              <Text style={styles.patientMeta}>
                {[
                  profile?.age != null ? `${profile.age} yrs` : null,
                  profile?.gender,
                  profile?.dob ? `DOB ${profile.dob}` : null,
                ].filter(Boolean).join(' · ')}
              </Text>
              <Text style={styles.patientId}>{patientId}</Text>
            </View>
          </View>
        </GlassCard>

        {/* ── Labs ────────────────────────────────────────────────────────── */}
        {!!plan.labs?.length && (
          <>
            <SectionLabel title="LABS ORDERED" />
            <GlassCard style={{ gap: Spacing.md }}>
              {plan.labs.map((lab, i) => (
                <View key={i} style={styles.labRow}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, flex: 1 }}>
                    <View style={[styles.urgencyBadge, { backgroundColor: `${URGENCY_COLOR[lab.urgency] ?? Colors.gray400}18`, borderColor: `${URGENCY_COLOR[lab.urgency] ?? Colors.gray400}40` }]}>
                      <Text style={[styles.urgencyText, { color: URGENCY_COLOR[lab.urgency] ?? Colors.gray400 }]}>{lab.urgency}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.labName}>{lab.name}</Text>
                      <Text style={styles.labTiming}>{lab.timing}</Text>
                    </View>
                  </View>
                  {!!lab.notes && (
                    <View style={styles.noteBox}>
                      <MaterialCommunityIcons name="information-outline" size={12} color={Colors.gray400} />
                      <Text style={styles.noteText}>{lab.notes}</Text>
                    </View>
                  )}
                  {i < (plan.labs?.length ?? 0) - 1 && <View style={styles.dividerLine} />}
                </View>
              ))}
            </GlassCard>
          </>
        )}

        {/* ── Medications ─────────────────────────────────────────────────── */}
        {!!plan.medications?.length && (
          <>
            <SectionLabel title="MEDICATIONS" />
            {plan.medications.map((med, i) => (
              <GlassCard key={i} style={styles.medCard}>
                <View style={styles.medHeader}>
                  <MaterialCommunityIcons name="pill" size={16} color={Colors.teal} />
                  <Text style={styles.medName}>{med.name}</Text>
                </View>
                <View style={styles.medChips}>
                  <View style={styles.doseChip}>
                    <Text style={styles.doseChipText}>{med.dose}</Text>
                  </View>
                  <View style={styles.doseChip}>
                    <Text style={styles.doseChipText}>{med.frequency}</Text>
                  </View>
                  <View style={[styles.routeChip, { backgroundColor: `${ROUTE_COLOR[med.route] ?? Colors.teal}18`, borderColor: `${ROUTE_COLOR[med.route] ?? Colors.teal}40` }]}>
                    <Text style={[styles.routeChipText, { color: ROUTE_COLOR[med.route] ?? Colors.teal }]}>{med.route}</Text>
                  </View>
                </View>
                {!!med.duration && (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <MaterialCommunityIcons name="calendar-range" size={13} color={Colors.gray400} />
                    <Text style={styles.medMeta}>Duration: {med.duration}</Text>
                  </View>
                )}
                {!!med.notes && (
                  <View style={styles.medNoteBox}>
                    <Text style={styles.medNoteText}>{med.notes}</Text>
                  </View>
                )}
              </GlassCard>
            ))}
          </>
        )}

        {/* ── Instructions ─────────────────────────────────────────────────── */}
        {!!plan.instructions && (
          <>
            <SectionLabel title="INSTRUCTIONS" />
            <GlassCard style={[styles.infoCard, { borderLeftColor: Colors.blue, borderLeftWidth: 4 }]}>
              <View style={styles.infoCardHeader}>
                <MaterialCommunityIcons name="clipboard-list-outline" size={16} color={Colors.blue} />
                <Text style={[styles.infoCardTitle, { color: Colors.blue }]}>Care Instructions</Text>
              </View>
              <Text style={styles.infoCardText}>{plan.instructions}</Text>
            </GlassCard>
          </>
        )}

        {/* ── Follow-up ────────────────────────────────────────────────────── */}
        {!!plan.follow_up && (
          <>
            <SectionLabel title="FOLLOW-UP" />
            <GlassCard style={[styles.infoCard, { borderLeftColor: Colors.teal, borderLeftWidth: 4 }]}>
              <View style={styles.infoCardHeader}>
                <MaterialCommunityIcons name="calendar-clock" size={16} color={Colors.teal} />
                <Text style={[styles.infoCardTitle, { color: Colors.teal }]}>Next Appointment</Text>
              </View>
              <Text style={styles.infoCardText}>{plan.follow_up}</Text>
            </GlassCard>
          </>
        )}

        {/* ── Diet ────────────────────────────────────────────────────────── */}
        {!!plan.diet && (
          <>
            <SectionLabel title="DIET PLAN" />
            <GlassCard style={[styles.infoCard, { borderLeftColor: Colors.green, borderLeftWidth: 4 }]}>
              <View style={styles.infoCardHeader}>
                <MaterialCommunityIcons name="food-apple-outline" size={16} color={Colors.green} />
                <Text style={[styles.infoCardTitle, { color: Colors.green }]}>Dietary Guidelines</Text>
              </View>
              <Text style={styles.infoCardText}>{plan.diet}</Text>
            </GlassCard>
          </>
        )}

        {/* ── Activity ─────────────────────────────────────────────────────── */}
        {!!plan.activity && (
          <>
            <SectionLabel title="ACTIVITY" />
            <GlassCard style={[styles.infoCard, { borderLeftColor: Colors.amber, borderLeftWidth: 4 }]}>
              <View style={styles.infoCardHeader}>
                <MaterialCommunityIcons name="run" size={16} color={Colors.amber} />
                <Text style={[styles.infoCardTitle, { color: Colors.amber }]}>Activity Guidelines</Text>
              </View>
              <Text style={styles.infoCardText}>{plan.activity}</Text>
            </GlassCard>
          </>
        )}

        {/* ── Share button ─────────────────────────────────────────────────── */}
        <TouchableOpacity style={styles.shareBtn} onPress={handleShare} disabled={sharing}>
          {sharing
            ? <ActivityIndicator size="small" color={Colors.navy} />
            : <MaterialCommunityIcons name="share-variant" size={18} color={Colors.navy} />}
          <Text style={styles.shareBtnText}>{sharing ? 'Preparing…' : 'Share / Download Care Plan'}</Text>
        </TouchableOpacity>

        <Text style={styles.legalNote}>
          This care plan was reviewed and approved by a licensed clinician.{'\n'}
          Please follow all instructions carefully and contact your doctor if you have questions.
        </Text>
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
  iconBtn:     { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  headerSub:   { color: Colors.gray600, fontSize: 10, fontWeight: '600', letterSpacing: 0.5 },
  scroll:      { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },

  // Pending state
  pendingWrap:      { flexGrow: 1, padding: Spacing.xl, alignItems: 'center', justifyContent: 'center', gap: Spacing.lg },
  pendingClockWrap: { width: 96, height: 96, borderRadius: 48, backgroundColor: `${Colors.amber}14`, borderWidth: 2, borderColor: `${Colors.amber}33`, alignItems: 'center', justifyContent: 'center' },
  pendingTitle:     { color: Colors.white, fontSize: 22, fontWeight: '800', textAlign: 'center' },
  pendingBody:      { color: Colors.gray400, fontSize: 14, lineHeight: 22, textAlign: 'center' },
  pendingInfoText:  { color: Colors.gray400, fontSize: 13, lineHeight: 20, flex: 1 },
  refreshBtn:       { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: Spacing.sm },
  refreshBtnText:   { color: Colors.teal, fontSize: 13, fontWeight: '600' },

  // Approval hero
  approvalHero:  { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xl, backgroundColor: `${Colors.teal}0C`, borderRadius: Radius.lg, borderWidth: 1, borderColor: `${Colors.teal}28` },
  approvalCheck: { width: 64, height: 64, borderRadius: 32, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center', marginBottom: Spacing.xs },
  approvalTitle: { color: Colors.white, fontSize: 20, fontWeight: '900' },
  approvalSub:   { color: Colors.gray400, fontSize: 12 },

  // Patient card
  patientCard: { gap: Spacing.md },
  patientRow:  { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatar:      { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  avatarText:  { color: Colors.navy, fontWeight: '900', fontSize: 20 },
  patientName: { color: Colors.white, fontSize: 17, fontWeight: '800' },
  patientMeta: { color: Colors.gray400, fontSize: 12 },
  patientId:   { color: Colors.gray600, fontSize: 11 },

  // Section label
  sectionLabel:     { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.xs },
  sectionLine:      { flex: 1, height: 1, backgroundColor: Colors.glassBorder },
  sectionLabelText: { color: Colors.gray600, fontSize: 10, fontWeight: '800', letterSpacing: 1.2 },

  // Labs
  labRow:       { gap: Spacing.xs },
  urgencyBadge: { borderWidth: 1, borderRadius: Radius.sm, paddingHorizontal: 8, paddingVertical: 3, alignItems: 'center' },
  urgencyText:  { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  labName:      { color: Colors.white, fontSize: 14, fontWeight: '700' },
  labTiming:    { color: Colors.gray400, fontSize: 12, marginTop: 1 },
  dividerLine:  { height: 1, backgroundColor: Colors.glassBorder, marginTop: Spacing.sm },
  noteBox:      { flexDirection: 'row', gap: 5, alignItems: 'flex-start', marginTop: 2 },
  noteText:     { color: Colors.gray400, fontSize: 11, lineHeight: 16, flex: 1 },

  // Medications
  medCard:     { gap: Spacing.sm },
  medHeader:   { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  medName:     { color: Colors.white, fontSize: 15, fontWeight: '800', flex: 1 },
  medChips:    { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  doseChip:    { backgroundColor: `${Colors.teal}18`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  doseChipText:{ color: Colors.teal, fontSize: 12, fontWeight: '600' },
  routeChip:   { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  routeChipText:{ fontSize: 12, fontWeight: '700' },
  medMeta:     { color: Colors.gray400, fontSize: 12 },
  medNoteBox:  { backgroundColor: `${Colors.gray600}18`, borderRadius: Radius.sm, padding: Spacing.sm },
  medNoteText: { color: Colors.gray400, fontSize: 12, lineHeight: 18, fontStyle: 'italic' },

  // Info cards (instructions / follow-up / diet / activity)
  infoCard:       { gap: Spacing.sm },
  infoCardHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  infoCardTitle:  { fontSize: 13, fontWeight: '800' },
  infoCardText:   { color: Colors.gray400, fontSize: 13, lineHeight: 21 },

  // Share button
  shareBtn:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, backgroundColor: Colors.teal, borderRadius: Radius.md, paddingVertical: Spacing.md + 2, marginTop: Spacing.sm },
  shareBtnText: { color: Colors.navy, fontSize: 15, fontWeight: '900' },

  legalNote: { color: Colors.gray600, fontSize: 10, textAlign: 'center', lineHeight: 15, paddingHorizontal: Spacing.md },
});
