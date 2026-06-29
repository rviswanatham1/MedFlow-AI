import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Button, Divider } from '../../components/ui';

// TODO: GET  /api/patient/referrals        → ServiceRequest FHIR resources
// TODO: POST /api/referrals/create         → create new referral request
// TODO: GET  /api/referrals/:id/status     → track referral status

type ReferralStatus = 'pending' | 'approved' | 'scheduled' | 'completed' | 'denied';

interface Referral {
  id: string;
  specialist: string;
  specialty: string;
  reason: string;
  requestedBy: string;
  requestDate: string;
  status: ReferralStatus;
  apptDate?: string;
  authRequired: boolean;
  authStatus?: 'pending' | 'approved' | 'denied';
  notes?: string;
}

const REFERRALS: Referral[] = [
  {
    id: 'ref-001', specialist: 'Dr. Sarah Chen', specialty: 'Cardiology',
    reason: 'Chest pain evaluation, ECG abnormality follow-up',
    requestedBy: 'Dr. Priya Patel', requestDate: 'Mar 30, 2026',
    status: 'scheduled', apptDate: 'Apr 14, 2026 · 9:30 AM',
    authRequired: true, authStatus: 'approved',
  },
  {
    id: 'ref-002', specialist: 'TBD', specialty: 'Orthopedics',
    reason: 'Chronic knee pain, rule out meniscus tear',
    requestedBy: 'Dr. Priya Patel', requestDate: 'Nov 21, 2025',
    status: 'pending', authRequired: true, authStatus: 'pending',
    notes: 'Prior auth submitted to BCBS. Awaiting response (3–5 business days).',
  },
  {
    id: 'ref-003', specialist: 'Dr. James Okafor', specialty: 'Dermatology',
    reason: 'Suspicious mole evaluation',
    requestedBy: 'Dr. Marcus Webb', requestDate: 'Aug 4, 2025',
    status: 'completed', apptDate: 'Sep 3, 2025',
    authRequired: false,
  },
];

const STATUS_CFG: Record<ReferralStatus, { label: string; color: string; icon: string }> = {
  pending:   { label: 'Pending',   color: Colors.amber,   icon: 'clock-outline'        },
  approved:  { label: 'Approved',  color: Colors.green,   icon: 'check-circle-outline' },
  scheduled: { label: 'Scheduled', color: Colors.blue,    icon: 'calendar-check'       },
  completed: { label: 'Completed', color: Colors.gray400, icon: 'check-all'            },
  denied:    { label: 'Denied',    color: Colors.red,     icon: 'close-circle-outline' },
};

const AUTH_CFG = {
  pending:  { label: 'Auth Pending',  color: Colors.amber },
  approved: { label: 'Auth Approved', color: Colors.green },
  denied:   { label: 'Auth Denied',   color: Colors.red   },
};

export default function ReferralsScreen() {
  const router = useRouter();
  const [expanded, setExpanded] = useState<string | null>('ref-001');

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Referrals</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* Stats */}
        <View style={styles.overviewRow}>
          {[
            { label: 'Active',    val: 2, color: Colors.teal   },
            { label: 'Pending',   val: 1, color: Colors.amber  },
            { label: 'Completed', val: 1, color: Colors.gray400},
          ].map(s => (
            <GlassCard key={s.label} style={styles.overviewCard}>
              <Text style={[styles.overviewVal, { color: s.color }]}>{s.val}</Text>
              <Text style={styles.overviewLabel}>{s.label}</Text>
            </GlassCard>
          ))}
        </View>

        {/* Referral cards */}
        {REFERRALS.map(ref => {
          const cfg = STATUS_CFG[ref.status];
          const isOpen = expanded === ref.id;
          return (
            <GlassCard key={ref.id} style={[styles.refCard, ref.status === 'denied' && styles.refCardDenied]}>
              <TouchableOpacity style={styles.refHeader} onPress={() => setExpanded(isOpen ? null : ref.id)}>
                <View style={[styles.refIconBg, { backgroundColor: `${cfg.color}18` }]}>
                  <MaterialCommunityIcons name={cfg.icon as any} size={18} color={cfg.color} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.refSpecialty}>{ref.specialty}</Text>
                  <Text style={styles.refSpecialist}>{ref.specialist}</Text>
                </View>
                <View style={styles.refStatusCol}>
                  <View style={[styles.statusBadge, { backgroundColor: `${cfg.color}18`, borderColor: `${cfg.color}44` }]}>
                    <Text style={[styles.statusText, { color: cfg.color }]}>{cfg.label}</Text>
                  </View>
                  <MaterialCommunityIcons name={isOpen ? 'chevron-up' : 'chevron-down'} size={16} color={Colors.gray400} style={{ marginTop: 4 }} />
                </View>
              </TouchableOpacity>

              {isOpen && (
                <View style={styles.refDetails}>
                  <Divider />
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Reason</Text>
                    <Text style={styles.detailVal}>{ref.reason}</Text>
                  </View>
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>Requested by</Text>
                    <Text style={styles.detailVal}>{ref.requestedBy} · {ref.requestDate}</Text>
                  </View>
                  {ref.apptDate && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailLabel}>Appointment</Text>
                      <Text style={[styles.detailVal, { color: Colors.teal }]}>{ref.apptDate}</Text>
                    </View>
                  )}
                  {ref.authRequired && ref.authStatus && (
                    <View style={styles.authRow}>
                      <MaterialCommunityIcons name="shield-check-outline" size={14} color={AUTH_CFG[ref.authStatus].color} />
                      <Text style={[styles.authText, { color: AUTH_CFG[ref.authStatus].color }]}>{AUTH_CFG[ref.authStatus].label}</Text>
                    </View>
                  )}
                  {ref.notes && (
                    <View style={styles.notesBox}>
                      <MaterialCommunityIcons name="information-outline" size={13} color={Colors.amber} />
                      <Text style={styles.notesText}>{ref.notes}</Text>
                    </View>
                  )}
                  {ref.status === 'scheduled' && (
                    <Button label="Add to Calendar" onPress={() => {}} variant="ghost" size="sm" style={{ marginTop: Spacing.xs }} />
                  )}
                </View>
              )}
            </GlassCard>
          );
        })}

        {/* Request new — clean, no description */}
        <GlassCard style={styles.newRefCard}>
          <Button
            label="Request a Specialist Referral"
            onPress={() => {
              // TODO: POST /api/referrals/create → triggers prior-auth check
            }}
            size="lg"
            style={{ width: '100%' }}
            icon={<MaterialCommunityIcons name="account-switch-outline" size={18} color={Colors.navy} />}
          />
        </GlassCard>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  overviewRow: { flexDirection: 'row', gap: Spacing.sm },
  overviewCard: { flex: 1, alignItems: 'center', gap: 4, paddingVertical: Spacing.md },
  overviewVal: { fontSize: 28, fontWeight: '900' },
  overviewLabel: { color: Colors.gray400, fontSize: 11, fontWeight: '600' },
  refCard: { gap: Spacing.sm },
  refCardDenied: { borderColor: `${Colors.red}44`, backgroundColor: `${Colors.red}06` },
  refHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  refIconBg: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  refSpecialty: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  refSpecialist: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  refStatusCol: { alignItems: 'flex-end' },
  statusBadge: { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  statusText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
  refDetails: { gap: Spacing.sm, paddingTop: Spacing.xs },
  detailRow: { gap: 3 },
  detailLabel: { color: Colors.gray600, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  detailVal: { color: Colors.white, fontSize: 13, fontWeight: '500' },
  authRow: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: Colors.navyLight, borderRadius: Radius.sm, padding: Spacing.xs + 2 },
  authText: { fontSize: 12, fontWeight: '700' },
  notesBox: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: `${Colors.amber}10`, borderWidth: 1, borderColor: `${Colors.amber}30`, borderRadius: Radius.sm, padding: Spacing.xs + 2 },
  notesText: { color: Colors.amber, fontSize: 11, flex: 1, lineHeight: 16 },
  newRefCard: { padding: Spacing.sm },
});
