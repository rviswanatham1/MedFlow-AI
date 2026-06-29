import React, { useRef, useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Animated, Dimensions, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Divider } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';

const { width } = Dimensions.get('window');

const QUICK_ACTIONS = [
  { id: 'book',      label: 'Book Visit', icon: 'calendar-month',         color: Colors.blue,  route: '/patient/book-appointment'  },
  { id: 'records',   label: 'My Records', icon: 'file-document-outline',  color: Colors.teal,  route: '/patient/records'           },
  { id: 'price',     label: 'Price Info', icon: 'currency-usd',           color: Colors.green, route: '/patient/price-estimate'    },
  { id: 'referrals', label: 'Referrals',  icon: 'account-switch-outline', color: Colors.red,   route: '/patient/referrals'         },
];

export default function PatientHome() {
  const router = useRouter();
  const { patientId, profile, setProfile, triageResult } = useApp();
  const fadeIn = useRef(new Animated.Value(0)).current;
  const [waitTime, setWaitTime] = useState(triageResult?.estimated_wait ?? null);
  const [queuePos, setQueuePos] = useState(triageResult?.queue_position ?? null);

  useEffect(() => {
    Animated.timing(fadeIn, { toValue: 1, duration: 700, useNativeDriver: true }).start();
    // load profile if not already cached
    if (!profile) {
      api.getPatientProfile(patientId).then(setProfile).catch(() => {});
    }
    // refresh live queue position
    api.getQueueStatus(patientId)
      .then(s => { setWaitTime(s.wait); setQueuePos(s.position); })
      .catch(() => {});
  }, [patientId]);

  const initials  = profile?.initials ?? '?';
  const firstName = profile?.name?.split(' ')[0] ?? 'there';

  // Recent visits from dataset as activity feed
  const recentVisits = (profile?.visits ?? []).slice(0, 3);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoRow}>
            <MaterialCommunityIcons name="heart-pulse" size={22} color={Colors.teal} />
            <Text style={styles.logoText}>MedFlow<Text style={styles.logoAI}>AI</Text></Text>
          </View>
          <View style={styles.headerRight}>
            <TouchableOpacity style={styles.notifBtn} onPress={() => router.push('/patient/notifications')}>
              <Ionicons name="notifications-outline" size={22} color={Colors.white} />
              <View style={styles.notifDot} />
            </TouchableOpacity>
            <TouchableOpacity style={styles.avatar} onPress={() => router.push('/patient/records')}>
              <Text style={styles.avatarText}>{initials}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <ScrollView style={{ flex: 1 }} contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Animated.View style={{ opacity: fadeIn, gap: Spacing.lg }}>


            {/* Wait time card */}
            <GlassCard style={styles.waitCard} glow>
              <View style={styles.waitCardInner}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.waitLabel}>Estimated Wait Time</Text>
                  <View style={styles.waitTimeRow}>
                    <Text style={styles.waitTime}>{waitTime ?? '—'}</Text>
                    {waitTime != null && <Text style={styles.waitMins}>min</Text>}
                  </View>
                  <Text style={styles.queuePos}>
                    {queuePos != null ? `${queuePos} in queue` : 'Not in queue'}
                  </Text>
                </View>
                <View style={styles.waitDial}>
                  <View style={styles.waitDialOuter}>
                    <View style={styles.waitDialInner}>
                      <Ionicons name="time" size={26} color={Colors.teal} />
                    </View>
                  </View>
                  <Text style={styles.waitDialLabel}>Live</Text>
                </View>
              </View>
              <TouchableOpacity style={styles.viewQueueBtn} onPress={() => router.push('/patient/wait-time')}>
                <Text style={styles.viewQueueText}>View queue status →</Text>
              </TouchableOpacity>
            </GlassCard>

            {/* Approved Report banner — shown when patient has been triaged */}
            {triageResult && (
              <TouchableOpacity
                style={styles.reportBanner}
                onPress={() => router.push('/patient/approved-report')}
              >
                <View style={styles.reportBannerLeft}>
                  <View style={styles.reportIconBg}>
                    <MaterialCommunityIcons name="file-check-outline" size={22} color={Colors.teal} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.reportBannerTitle}>Your Care Plan</Text>
                    <Text style={styles.reportBannerSub}>View your doctor-approved care plan</Text>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.teal} />
              </TouchableOpacity>
            )}

            {/* Start Check-In CTA */}
            <TouchableOpacity style={styles.checkinCTA} onPress={() => router.push('/patient/symptom-input')}>
              <View style={styles.checkinLeft}>
                <View style={styles.checkinIconBg}>
                  <Ionicons name="add-circle" size={26} color={Colors.navy} />
                </View>
                <Text style={styles.checkinTitle}>Start Check-In</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={Colors.navy} />
            </TouchableOpacity>

            {/* Quick actions */}
            <View>
              <Text style={styles.sectionTitle}>Quick Actions</Text>
              <View style={styles.quickGrid}>
                {QUICK_ACTIONS.map(action => (
                  <TouchableOpacity
                    key={action.id}
                    style={styles.quickCard}
                    onPress={() => router.push(action.route as any)}
                  >
                    <View style={[styles.quickIcon, { backgroundColor: `${action.color}18` }]}>
                      <MaterialCommunityIcons name={action.icon as any} size={24} color={action.color} />
                    </View>
                    <Text style={styles.quickLabel}>{action.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* Recent visits from dataset */}
            <View>
              <Text style={styles.sectionTitle}>Recent Visits</Text>
              <GlassCard>
                {recentVisits.length === 0 ? (
                  <Text style={{ color: Colors.gray400, fontSize: 13 }}>No past visits on record.</Text>
                ) : recentVisits.map((v, i) => (
                  <View key={v.encounter_id}>
                    <TouchableOpacity style={styles.activityRow} onPress={() => router.push('/patient/records')}>
                      <View style={[styles.activityIcon, { backgroundColor: `${Colors.teal}18` }]}>
                        <MaterialCommunityIcons name="calendar-check" size={18} color={Colors.teal} />
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.activityText} numberOfLines={1}>
                          {v.symptoms.charAt(0).toUpperCase() + v.symptoms.slice(1)}
                        </Text>
                        <Text style={styles.activityTime}>{v.date}</Text>
                      </View>
                      {v.heart_rate != null && (
                        <Text style={styles.vitalChip}>HR {v.heart_rate}</Text>
                      )}
                    </TouchableOpacity>
                    {i < recentVisits.length - 1 && <Divider />}
                  </View>
                ))}
              </GlassCard>
            </View>

          </Animated.View>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.navyMid },
  container: { flex: 1, backgroundColor: Colors.navy },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, backgroundColor: Colors.navyMid, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  logoRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  logoText: { color: Colors.white, fontSize: 20, fontWeight: '900', letterSpacing: -0.5 },
  logoAI: { color: Colors.teal },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  notifBtn: { position: 'relative', padding: 4 },
  notifDot: { position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.red, borderWidth: 1.5, borderColor: Colors.navyMid },
  avatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: Colors.navy, fontWeight: '800', fontSize: 13 },
  scroll: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  greetRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  greetText: { color: Colors.white, fontSize: 22, fontWeight: '800' },
  conditionBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.amber}18`, borderWidth: 1, borderColor: `${Colors.amber}44`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  conditionBadgeText: { color: Colors.amber, fontSize: 11, fontWeight: '700' },
  conditionsRow: { flexDirection: 'row', gap: Spacing.xs, paddingBottom: 2 },
  conditionChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full, paddingHorizontal: 12, paddingVertical: 5 },
  conditionDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.red },
  conditionChipText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  waitCard: { gap: Spacing.md },
  waitCardInner: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  waitLabel: { color: Colors.gray400, fontSize: 12, fontWeight: '600', letterSpacing: 0.5, marginBottom: 4 },
  waitTimeRow: { flexDirection: 'row', alignItems: 'baseline', gap: 4 },
  waitTime: { color: Colors.teal, fontSize: 52, fontWeight: '900', letterSpacing: -2 },
  waitMins: { color: Colors.teal, fontSize: 20, fontWeight: '600' },
  queuePos: { color: Colors.gray400, fontSize: 13, marginTop: 4 },
  waitDial: { alignItems: 'center', gap: 6 },
  waitDialOuter: { width: 68, height: 68, borderRadius: 34, backgroundColor: Colors.tealDim, borderWidth: 2, borderColor: `${Colors.teal}44`, alignItems: 'center', justifyContent: 'center' },
  waitDialInner: { width: 50, height: 50, borderRadius: 25, backgroundColor: Colors.tealDim2, alignItems: 'center', justifyContent: 'center' },
  waitDialLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  viewQueueBtn: { borderTopWidth: 1, borderTopColor: Colors.glassBorder, paddingTop: Spacing.sm },
  viewQueueText: { color: Colors.teal, fontSize: 13, fontWeight: '600' },
  reportBanner: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}44`,
    borderRadius: Radius.lg, padding: Spacing.md,
  },
  reportBannerLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, flex: 1 },
  reportIconBg: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: `${Colors.teal}18`, borderWidth: 1, borderColor: `${Colors.teal}33`,
    alignItems: 'center', justifyContent: 'center',
  },
  reportBannerTitle: { color: Colors.teal, fontSize: 14, fontWeight: '800' },
  reportBannerSub: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  checkinCTA: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: Colors.teal, borderRadius: Radius.lg, padding: Spacing.md },
  checkinLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  checkinIconBg: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(0,0,0,0.15)', alignItems: 'center', justifyContent: 'center' },
  checkinTitle: { color: Colors.navy, fontSize: 16, fontWeight: '800' },
  sectionTitle: { color: Colors.white, fontSize: 17, fontWeight: '700', marginBottom: Spacing.sm },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  quickCard: { width: (width - Spacing.lg * 2 - Spacing.sm) / 2, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.md, gap: Spacing.sm },
  quickIcon: { width: 46, height: 46, borderRadius: Radius.sm, alignItems: 'center', justifyContent: 'center' },
  quickLabel: { color: Colors.white, fontSize: 13, fontWeight: '700' },
  activityRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, paddingVertical: Spacing.xs + 2 },
  activityIcon: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  activityText: { color: Colors.white, fontSize: 13, fontWeight: '500' },
  activityTime: { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  vitalChip: { color: Colors.teal, fontSize: 11, fontWeight: '700', backgroundColor: Colors.tealDim, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
});
