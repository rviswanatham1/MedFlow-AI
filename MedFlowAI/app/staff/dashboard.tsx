import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Animated, Dimensions, SafeAreaView, RefreshControl, ActivityIndicator,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, UrgencyIndicator, SectionHeader, Badge, ConfidenceBar } from '../../components/ui';
import { api, QueueEntry, AnalyticsSummary, ApprovedReport, CarePlan } from '../../services/api';

type PendingCarePlan = { patient_id: string; approved_at: string; approved_by: string; urgency: string; summary: string; pathway: string };
import { useApp } from '../../context/AppContext';

const { width } = Dimensions.get('window');

// ── Approved patient card (staff view) ───────────────────────────────────────
interface ApprovedPatientData {
  queue: QueueEntry;
  report: ApprovedReport | null;
  carePlan: CarePlan | null;
}

function ApprovedPatientCard({ data, onPress }: { data: ApprovedPatientData; onPress: () => void }) {
  const { queue: p, report, carePlan } = data;
  const hasSOAP = !!(report?.soap_note);
  const hasMeds = !!(carePlan?.medications?.length);
  const hasLabs = !!(carePlan?.labs?.length);

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.85}>
      <GlassCard style={styles.approvedCard}>
        {/* Top row */}
        <View style={styles.approvedCardTop}>
          <View style={styles.approvedCardLeft}>
            <View style={styles.approvedAvatar}>
              <Text style={styles.approvedAvatarText}>{p.patient_id.slice(-2)}</Text>
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={styles.approvedPatientId}>{p.patient_id}</Text>
              {p.age != null && (
                <Text style={styles.approvedPatientMeta}>{p.age}y {p.gender ?? ''}</Text>
              )}
            </View>
          </View>
          <View style={styles.approvedStamp}>
            <MaterialCommunityIcons name="check-circle" size={13} color={Colors.teal} />
            <Text style={styles.approvedStampText}>
              {report?.approved_by ? `Dr. ${report.approved_by.replace(/^DR\d+\s*/i, '')}` : 'Approved'}
            </Text>
          </View>
        </View>

        {/* Summary */}
        {p.summary ? (
          <Text style={styles.approvedSummary} numberOfLines={2}>{p.summary}</Text>
        ) : null}

        {/* Document chips */}
        <View style={styles.docChips}>
          <View style={[styles.docChip, { backgroundColor: `${Colors.blue}15`, borderColor: `${Colors.blue}33` }]}>
            <MaterialCommunityIcons name="file-document-outline" size={11} color={Colors.blue} />
            <Text style={[styles.docChipText, { color: Colors.blue }]}>SOAP</Text>
            {hasSOAP && <View style={styles.docChipDot} />}
          </View>
          <View style={[styles.docChip, { backgroundColor: `${Colors.teal}15`, borderColor: `${Colors.teal}33` }]}>
            <MaterialCommunityIcons name="test-tube" size={11} color={Colors.teal} />
            <Text style={[styles.docChipText, { color: Colors.teal }]}>Labs</Text>
            {hasLabs && <View style={[styles.docChipDot, { backgroundColor: Colors.teal }]} />}
          </View>
          <View style={[styles.docChip, { backgroundColor: `${Colors.green}15`, borderColor: `${Colors.green}33` }]}>
            <MaterialCommunityIcons name="pill" size={11} color={Colors.green} />
            <Text style={[styles.docChipText, { color: Colors.green }]}>Meds</Text>
            {hasMeds && <View style={[styles.docChipDot, { backgroundColor: Colors.green }]} />}
          </View>
        </View>

        {/* Pathway + View button */}
        <View style={styles.approvedCardFooter}>
          <View style={styles.pathwayChip}>
            <MaterialCommunityIcons name="source-fork" size={11} color={Colors.blue} />
            <Text style={styles.pathwayText}>{p.pathway}</Text>
          </View>
          <View style={styles.viewDocsBtn}>
            <Text style={styles.viewDocsBtnText}>View Documents</Text>
            <Ionicons name="chevron-forward" size={13} color={Colors.teal} />
          </View>
        </View>
      </GlassCard>
    </TouchableOpacity>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────────
export default function StaffDashboard() {
  const router  = useRouter();
  const { clinicianId, isDoctor } = useApp();
  const fadeIn  = useRef(new Animated.Value(0)).current;

  const [summary,          setSummary]          = useState<AnalyticsSummary | null>(null);
  const [queue,            setQueue]            = useState<QueueEntry[]>([]);
  const [approvedData,     setApprovedData]     = useState<ApprovedPatientData[]>([]);
  const [loadingApproved,  setLoadingApproved]  = useState(false);
  const [pendingCarePlans, setPendingCarePlans] = useState<PendingCarePlan[]>([]);
  const [refreshing,       setRefreshing]       = useState(false);

  // Pending list for doctor view only
  const pending = queue
    .filter(p => p.status !== 'approved')
    .sort((a, b) => {
      const o: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
      return (o[a.urgency] ?? 2) - (o[b.urgency] ?? 2);
    })
    .slice(0, 5);

  const approved = queue.filter(p => p.status === 'approved');

  const loadApprovedDocs = useCallback(async (approvedQueue: QueueEntry[]) => {
    if (!approvedQueue.length) { setApprovedData([]); return; }
    setLoadingApproved(true);
    const results = await Promise.allSettled(
      approvedQueue.slice(0, 6).map(async (p) => {
        const [report, carePlan] = await Promise.allSettled([
          api.getApprovedReport(p.patient_id),
          api.getCarePlan(p.patient_id, 'staff'),
        ]);
        return {
          queue: p,
          report:   report.status   === 'fulfilled' ? report.value   : null,
          carePlan: carePlan.status === 'fulfilled' ? carePlan.value : null,
        } as ApprovedPatientData;
      })
    );
    setApprovedData(results.filter(r => r.status === 'fulfilled').map(r => (r as any).value));
    setLoadingApproved(false);
  }, []);

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(false);
    try {
      const [sum, q] = await Promise.all([api.getAnalyticsSummary(), api.getQueue()]);
      setSummary(sum);
      setQueue(q);
      if (isDoctor) {
        api.getPendingCarePlans().then(setPendingCarePlans).catch(() => {});
      } else {
        const approvedQ = q.filter(p => p.status === 'approved');
        await loadApprovedDocs(approvedQ);
      }
    } catch {}
    finally { setRefreshing(false); }
  }, [isDoctor, loadApprovedDocs]);

  useEffect(() => {
    Animated.timing(fadeIn, { toValue: 1, duration: 700, useNativeDriver: true }).start();
  }, []);

  useFocusEffect(useCallback(() => { loadData(); }, [loadData]));

  const onRefresh = () => { setRefreshing(true); loadData(true); };

  const activeCount  = pending.length > 0 ? pending.length : (summary?.active_patients ?? 0);
  const pendingCount = pending.filter(p => p.status === 'pending_review').length;
  const escalations  = pending.filter(p => p.urgency === 'critical').length;
  const avgWait      = summary?.avg_wait ?? (summary as any)?.avg_wait_minutes ?? 0;

  const metrics = [
    { label: 'Active Patients', value: summary ? String(summary.active_patients) : '—', color: Colors.teal,  icon: 'account-group-outline' },
    { label: 'Avg Wait',        value: avgWait ? `${avgWait}m` : '—',                   color: Colors.green, icon: 'clock-outline' },
    { label: 'Pending Review',  value: String(pendingCount),                             color: Colors.amber, icon: 'clipboard-text-outline' },
    { label: 'Approved',        value: String(approved.length),                          color: isDoctor ? Colors.red : Colors.teal, icon: isDoctor ? 'alert-outline' : 'check-circle-outline' },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navyMid }}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoRow}>
            <MaterialCommunityIcons name="heart-pulse" size={20} color={Colors.teal} />
            <Text style={styles.logoText}>MedFlow<Text style={styles.logoAI}>AI</Text></Text>
            <View style={[styles.staffBadge, isDoctor && { backgroundColor: `${Colors.blue}33` }]}>
              <Text style={[styles.staffBadgeText, isDoctor && { color: Colors.blue }]}>{isDoctor ? 'DOCTOR' : 'STAFF'}</Text>
            </View>
          </View>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>AM</Text>
          </View>
        </View>

        {/* Nav */}
        <View style={styles.navTabs}>
          {[
            { label: 'Overview',  route: '/staff/dashboard',     active: true },
            { label: 'Queue',     route: '/staff/patient-queue', active: false },
            ...(!isDoctor ? [{ label: 'Analytics', route: '/staff/analytics', active: false }] : []),
          ].map(tab => (
            <TouchableOpacity key={tab.label} style={styles.navTab} onPress={() => router.push(tab.route as any)}>
              <Text style={[styles.navTabText, tab.active && styles.navTabTextActive]}>{tab.label}</Text>
              {tab.active && <View style={styles.navTabIndicator} />}
            </TouchableOpacity>
          ))}
        </View>

        <ScrollView
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.teal} />}
        >
          <Animated.View style={{ opacity: fadeIn, gap: Spacing.lg }}>

            {/* Metrics */}
            <View style={styles.metricsGrid}>
              {metrics.map(m => (
                <GlassCard key={m.label} style={styles.metricCard}>
                  <MaterialCommunityIcons name={m.icon as any} size={18} color={m.color} />
                  <Text style={[styles.metricVal, { color: m.color }]}>{m.value}</Text>
                  <Text style={styles.metricLabel}>{m.label}</Text>
                </GlassCard>
              ))}
            </View>

            {/* Quick access */}
            <View style={styles.quickAccessRow}>
              {(isDoctor ? [
                { label: 'Patient Search', icon: 'account-search-outline', color: Colors.teal,  route: '/staff/patient-search' },
              ] : [
                { label: 'Patient Search', icon: 'account-search-outline', color: Colors.teal,  route: '/staff/patient-search'     },
                { label: 'Resources',      icon: 'floor-plan',             color: Colors.blue,  route: '/staff/resource-allocation' },
              ]).map(q => (
                <TouchableOpacity key={q.label} style={styles.quickAccessCard} onPress={() => router.push(q.route as any)}>
                  <View style={[styles.quickAccessIcon, { backgroundColor: `${q.color}18` }]}>
                    <MaterialCommunityIcons name={q.icon as any} size={20} color={q.color} />
                  </View>
                  <Text style={styles.quickAccessLabel}>{q.label}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Escalation alert */}
            {escalations > 0 && (
              <View style={styles.alertBanner}>
                <MaterialCommunityIcons name="alert-circle" size={20} color={Colors.red} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.alertTitle}>{escalations} Escalation{escalations > 1 ? 's' : ''} Need{escalations === 1 ? 's' : ''} Immediate Attention</Text>
                  <Text style={styles.alertText}>Check the patient queue for critical flags</Text>
                </View>
                <TouchableOpacity style={styles.alertBtn} onPress={() => router.push('/staff/patient-queue')}>
                  <Text style={styles.alertBtnText}>View</Text>
                </TouchableOpacity>
              </View>
            )}

            {/* ── DOCTOR VIEW: Pending AI Reviews ── */}
            {isDoctor && (
              <View>
                <SectionHeader
                  title="Pending AI Reviews"
                  action={{ label: 'See all', onPress: () => router.push('/staff/patient-queue') }}
                />
                {pending.length === 0 ? (
                  <GlassCard style={{ alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.lg }}>
                    <MaterialCommunityIcons name="check-circle-outline" size={36} color={Colors.teal} />
                    <Text style={{ color: Colors.teal, fontSize: 14, fontWeight: '700' }}>All caught up!</Text>
                    <Text style={{ color: Colors.gray400, fontSize: 12, textAlign: 'center' }}>No pending AI reviews. Pull down to refresh.</Text>
                  </GlassCard>
                ) : pending.map(patient => (
                  <TouchableOpacity key={patient.patient_id} onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: patient.patient_id } })}>
                    <GlassCard style={[styles.reviewCard, patient.urgency === 'critical' && styles.reviewCardCritical]}>
                      <View style={styles.reviewHeader}>
                        <View style={styles.reviewIdRow}>
                          <Text style={styles.reviewId}>{patient.patient_id}</Text>
                          {patient.age != null && <Badge label={`${patient.age}y ${patient.gender ?? ''}`} />}
                        </View>
                        <UrgencyIndicator level={patient.urgency as any} />
                      </View>
                      {patient.summary ? <Text style={styles.reviewSummary}>{patient.summary}</Text> : null}
                      {patient.confidence != null && <ConfidenceBar score={patient.confidence} label="AI Confidence" />}
                      <View style={styles.reviewFooter}>
                        <View style={styles.pathwayChip}>
                          <MaterialCommunityIcons name="source-fork" size={12} color={Colors.blue} />
                          <Text style={styles.pathwayText}>{patient.pathway}</Text>
                        </View>
                        <Text style={[styles.waitText, patient.wait === 0 && { color: Colors.red }]}>
                          {patient.wait === 0 ? 'IMMEDIATE' : `${patient.wait}m`}
                        </Text>
                      </View>
                      {patient.flag && (
                        <View style={[styles.flagRow, { borderColor: patient.urgency === 'critical' ? `${Colors.red}40` : `${Colors.teal}30` }]}>
                          <MaterialCommunityIcons name={patient.urgency === 'critical' ? 'alert-circle-outline' : 'information-outline'} size={13} color={patient.urgency === 'critical' ? Colors.red : Colors.teal} />
                          <Text style={[styles.flagText, { color: patient.urgency === 'critical' ? Colors.red : Colors.teal }]}>{patient.flag}</Text>
                        </View>
                      )}
                      <View style={styles.reviewActions}>
                        <TouchableOpacity style={styles.approveBtn} onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: patient.patient_id } })}>
                          <MaterialCommunityIcons name="check" size={15} color={Colors.navy} />
                          <Text style={styles.approveBtnText}>Approve</Text>
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.modifyBtn} onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: patient.patient_id } })}>
                          <Text style={styles.modifyBtnText}>Review</Text>
                        </TouchableOpacity>
                      </View>
                    </GlassCard>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {/* ── DOCTOR VIEW: Create / Edit Care Plan ── */}
            {isDoctor && pendingCarePlans.length > 0 && (
              <View style={{ gap: Spacing.sm }}>
                <SectionHeader
                  title="Care Plans Required"
                  action={{ label: 'See all', onPress: () => router.push('/staff/patient-queue') }}
                />
                {pendingCarePlans.map(p => {
                  const urgencyColor: Record<string, string> = { critical: Colors.red, high: Colors.amber, medium: Colors.blue, low: Colors.green };
                  const uc = urgencyColor[p.urgency] ?? Colors.blue;
                  return (
                    <GlassCard key={p.patient_id} style={styles.carePlanCard}>
                      <View style={styles.carePlanCardTop}>
                        <View style={styles.carePlanCardLeft}>
                          <View style={[styles.carePlanAvatar, { backgroundColor: `${uc}18`, borderColor: `${uc}44` }]}>
                            <MaterialCommunityIcons name="clipboard-pulse-outline" size={18} color={uc} />
                          </View>
                          <View style={{ flex: 1, gap: 2 }}>
                            <Text style={styles.carePlanPatientId}>{p.patient_id}</Text>
                            <Text style={styles.carePlanMeta}>
                              Diagnosis approved{p.approved_at ? ` · ${new Date(p.approved_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : ''}
                            </Text>
                          </View>
                        </View>
                        <View style={[styles.diagApprovedBadge]}>
                          <MaterialCommunityIcons name="check-circle" size={11} color={Colors.teal} />
                          <Text style={styles.diagApprovedText}>Dx Approved</Text>
                        </View>
                      </View>
                      {p.summary ? (
                        <Text style={styles.carePlanSummary} numberOfLines={2}>{p.summary}</Text>
                      ) : null}
                      <TouchableOpacity
                        style={styles.createCarePlanBtn}
                        onPress={() => router.push({ pathname: '/staff/care-plan', params: { id: p.patient_id } } as any)}
                      >
                        <MaterialCommunityIcons name="plus-circle-outline" size={16} color={Colors.navy} />
                        <Text style={styles.createCarePlanBtnText}>Create Care Plan</Text>
                      </TouchableOpacity>
                    </GlassCard>
                  );
                })}
              </View>
            )}

            {/* ── STAFF VIEW: Approved Documents ── */}
            {!isDoctor && (
              <View style={{ gap: Spacing.sm }}>
                <SectionHeader
                  title="Approved Documents"
                  action={{ label: 'See all', onPress: () => router.push('/staff/patient-queue') }}
                />

                {loadingApproved ? (
                  <GlassCard style={{ alignItems: 'center', paddingVertical: Spacing.xl, gap: Spacing.sm }}>
                    <ActivityIndicator color={Colors.teal} />
                    <Text style={{ color: Colors.gray400, fontSize: 13 }}>Loading approved records…</Text>
                  </GlassCard>
                ) : approvedData.length === 0 ? (
                  <GlassCard style={{ alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xl }}>
                    <View style={styles.noDocsIconWrap}>
                      <MaterialCommunityIcons name="file-document-multiple-outline" size={36} color={Colors.gray600} />
                    </View>
                    <Text style={styles.noDocsTitle}>No Approved Documents Yet</Text>
                    <Text style={styles.noDocsBody}>
                      Documents will appear here once a doctor reviews and approves a patient's triage report.
                    </Text>
                    <TouchableOpacity style={styles.viewQueueBtn} onPress={() => router.push('/staff/patient-queue')}>
                      <MaterialCommunityIcons name="clipboard-list-outline" size={14} color={Colors.teal} />
                      <Text style={styles.viewQueueBtnText}>View Patient Queue</Text>
                    </TouchableOpacity>
                  </GlassCard>
                ) : (
                  approvedData.map(data => (
                    <ApprovedPatientCard
                      key={data.queue.patient_id}
                      data={data}
                      onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: data.queue.patient_id } })}
                    />
                  ))
                )}
              </View>
            )}

            {/* Forecast — hidden for doctors */}
            {!isDoctor && (
              <GlassCard style={styles.forecastCard}>
                <View style={styles.forecastHeader}>
                  <MaterialCommunityIcons name="chart-bar" size={20} color={Colors.blue} />
                  <Text style={styles.forecastTitle}>AI Operational Forecast</Text>
                </View>
                <Text style={styles.forecastText}>
                  {summary?.forecast ?? 'Peak volume expected 2–5 PM. Recommend 2 additional nursing staff and opening overflow bay 3.'}
                </Text>
                <TouchableOpacity onPress={() => router.push('/staff/analytics')}>
                  <Text style={styles.forecastLink}>View full analytics →</Text>
                </TouchableOpacity>
              </GlassCard>
            )}

          </Animated.View>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: Colors.navy },
  header:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, backgroundColor: Colors.navyMid, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  logoRow:      { flexDirection: 'row', alignItems: 'center', gap: 7 },
  logoText:     { color: Colors.white, fontSize: 20, fontWeight: '900', letterSpacing: -0.5 },
  logoAI:       { color: Colors.teal },
  staffBadge:   { backgroundColor: `${Colors.blue}22`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  staffBadgeText: { color: Colors.blue, fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  avatar:       { width: 36, height: 36, borderRadius: 18, backgroundColor: Colors.blue, alignItems: 'center', justifyContent: 'center' },
  avatarText:   { color: Colors.white, fontWeight: '800', fontSize: 13 },
  navTabs:         { flexDirection: 'row', backgroundColor: Colors.navyMid, paddingHorizontal: Spacing.lg, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  navTab:          { paddingVertical: 13, marginRight: Spacing.lg, alignItems: 'center' },
  navTabActive:    {},
  navTabIndicator: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 2, backgroundColor: Colors.teal, borderRadius: 1 },
  navTabText:      { color: Colors.white, fontSize: 14, fontWeight: '600', opacity: 0.55 },
  navTabTextActive:{ color: Colors.teal, opacity: 1 },
  scroll:       { padding: Spacing.lg, paddingBottom: Spacing.xxl },

  metricsGrid:  { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  metricCard:   { width: (width - Spacing.lg * 2 - Spacing.sm) / 2, gap: 2, alignItems: 'flex-start' },
  metricVal:    { fontSize: 28, fontWeight: '900', letterSpacing: -0.5, marginTop: 4 },
  metricLabel:  { color: Colors.gray400, fontSize: 11, fontWeight: '600' },

  quickAccessRow:   { flexDirection: 'row', gap: Spacing.sm },
  quickAccessCard:  { flex: 1, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.sm, alignItems: 'center', gap: Spacing.xs },
  quickAccessIcon:  { width: 40, height: 40, borderRadius: Radius.sm, alignItems: 'center', justifyContent: 'center' },
  quickAccessLabel: { color: Colors.gray400, fontSize: 10, fontWeight: '600', textAlign: 'center' },

  alertBanner:  { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.red}12`, borderWidth: 1, borderColor: `${Colors.red}40`, borderRadius: Radius.md, padding: Spacing.md },
  alertTitle:   { color: Colors.red, fontSize: 13, fontWeight: '700' },
  alertText:    { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  alertBtn:     { backgroundColor: Colors.red, borderRadius: Radius.sm, paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2 },
  alertBtnText: { color: Colors.white, fontWeight: '700', fontSize: 13 },

  // Doctor pending review cards
  reviewCard:         { marginBottom: Spacing.sm, gap: Spacing.sm },
  reviewCardCritical: { borderColor: `${Colors.red}55`, backgroundColor: `${Colors.red}06` },
  reviewHeader:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  reviewIdRow:        { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  reviewId:           { color: Colors.white, fontSize: 16, fontWeight: '800' },
  reviewSummary:      { color: Colors.gray400, fontSize: 13, lineHeight: 19 },
  reviewFooter:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  reviewActions:      { flexDirection: 'row', gap: Spacing.sm },
  approveBtn:         { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: Colors.teal, borderRadius: Radius.sm, paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2 },
  approveBtnText:     { color: Colors.navy, fontWeight: '700', fontSize: 13 },
  modifyBtn:          { flex: 1, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingVertical: Spacing.xs + 2, alignItems: 'center' },
  modifyBtnText:      { color: Colors.gray400, fontWeight: '600', fontSize: 13 },

  // Staff approved document cards
  approvedCard:       { gap: Spacing.sm, marginBottom: Spacing.xs },
  approvedCardTop:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  approvedCardLeft:   { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, flex: 1 },
  approvedAvatar:     { width: 40, height: 40, borderRadius: 20, backgroundColor: `${Colors.teal}20`, borderWidth: 1, borderColor: `${Colors.teal}44`, alignItems: 'center', justifyContent: 'center' },
  approvedAvatarText: { color: Colors.teal, fontWeight: '900', fontSize: 13 },
  approvedPatientId:  { color: Colors.white, fontSize: 15, fontWeight: '800' },
  approvedPatientMeta:{ color: Colors.gray400, fontSize: 11 },
  approvedStamp:      { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.teal}14`, borderWidth: 1, borderColor: `${Colors.teal}33`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  approvedStampText:  { color: Colors.teal, fontSize: 11, fontWeight: '700' },
  approvedSummary:    { color: Colors.gray400, fontSize: 12, lineHeight: 18 },
  docChips:           { flexDirection: 'row', gap: Spacing.xs },
  docChip:            { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3 },
  docChipText:        { fontSize: 11, fontWeight: '600' },
  docChipDot:         { width: 5, height: 5, borderRadius: 2.5, backgroundColor: Colors.blue, marginLeft: 1 },
  approvedCardFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: Spacing.xs, borderTopWidth: 1, borderTopColor: Colors.glassBorder },
  viewDocsBtn:        { flexDirection: 'row', alignItems: 'center', gap: 4 },
  viewDocsBtnText:    { color: Colors.teal, fontSize: 12, fontWeight: '700' },

  pathwayChip:  { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.blue}18`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  pathwayText:  { color: Colors.blue, fontSize: 12, fontWeight: '600' },
  waitText:     { color: Colors.amber, fontSize: 12, fontWeight: '700' },
  flagRow:      { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: Colors.navyLight, borderWidth: 1, borderRadius: Radius.sm, padding: Spacing.xs + 2 },
  flagText:     { fontSize: 11, flex: 1, lineHeight: 16 },

  // Empty state
  noDocsIconWrap: { width: 72, height: 72, borderRadius: 36, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, alignItems: 'center', justifyContent: 'center' },
  noDocsTitle:    { color: Colors.white, fontSize: 15, fontWeight: '700' },
  noDocsBody:     { color: Colors.gray400, fontSize: 13, textAlign: 'center', lineHeight: 20, paddingHorizontal: Spacing.md },
  viewQueueBtn:   { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderColor: `${Colors.teal}44`, borderRadius: Radius.full, paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2 },
  viewQueueBtnText: { color: Colors.teal, fontSize: 13, fontWeight: '700' },

  // Care plan pending cards (doctor view)
  carePlanCard:         { gap: Spacing.sm, borderColor: `${Colors.teal}25`, borderWidth: 1, marginBottom: Spacing.xs },
  carePlanCardTop:      { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  carePlanCardLeft:     { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, flex: 1 },
  carePlanAvatar:       { width: 40, height: 40, borderRadius: 12, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  carePlanPatientId:    { color: Colors.white, fontSize: 15, fontWeight: '800' },
  carePlanMeta:         { color: Colors.gray400, fontSize: 11 },
  diagApprovedBadge:    { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.teal}14`, borderWidth: 1, borderColor: `${Colors.teal}33`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3 },
  diagApprovedText:     { color: Colors.teal, fontSize: 10, fontWeight: '700' },
  carePlanSummary:      { color: Colors.gray400, fontSize: 12, lineHeight: 18 },
  createCarePlanBtn:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, backgroundColor: Colors.teal, borderRadius: Radius.md, paddingVertical: Spacing.sm + 2 },
  createCarePlanBtnText:{ color: Colors.navy, fontSize: 14, fontWeight: '800' },

  forecastCard:   { gap: Spacing.sm },
  forecastHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  forecastTitle:  { color: Colors.white, fontSize: 15, fontWeight: '700' },
  forecastText:   { color: Colors.gray400, fontSize: 13, lineHeight: 20 },
  forecastLink:   { color: Colors.blue, fontSize: 13, fontWeight: '600' },
});
