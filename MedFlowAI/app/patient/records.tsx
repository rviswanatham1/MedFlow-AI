import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Badge, Divider } from '../../components/ui';
import { useApp } from '../../context/AppContext';

type Tab = 'visits' | 'conditions' | 'vitals';

export default function RecordsScreen() {
  const router = useRouter();
  const { profile } = useApp();
  const [tab, setTab] = useState<Tab>('visits');

  const TABS: { key: Tab; label: string; icon: string }[] = [
    { key: 'visits',     label: 'Visits',     icon: 'calendar-clock' },
    { key: 'conditions', label: 'Conditions', icon: 'medical-bag'    },
    { key: 'vitals',     label: 'Vitals',     icon: 'heart-pulse'    },
  ];

  const visits     = profile?.visits     ?? [];
  const conditions = profile?.conditions ?? [];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>My Records</Text>
        <View style={{ width: 40 }} />
      </View>

      {/* Patient banner */}
      {profile && (
        <GlassCard style={styles.patientBanner}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>{profile.initials}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.patientName}>{profile.name}</Text>
            <Text style={styles.patientMeta}>
              {profile.age != null ? `${profile.age} yrs` : ''}
              {profile.gender ? ` · ${profile.gender}` : ''}
              {profile.dob   ? ` · DOB: ${profile.dob}` : ''}
            </Text>
            <Text style={styles.patientId}>{profile.patient_id}</Text>
          </View>
        </GlassCard>
      )}

      {/* Tabs */}
      <View style={styles.tabRow}>
        {TABS.map(t => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, tab === t.key && styles.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <MaterialCommunityIcons
              name={t.icon as any}
              size={15}
              color={tab === t.key ? Colors.teal : Colors.gray400}
            />
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>{t.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ── VISITS ── */}
        {tab === 'visits' && (
          <View style={{ gap: Spacing.sm }}>
            {visits.length === 0 ? (
              <Text style={styles.emptyText}>No visits on record.</Text>
            ) : visits.map((v) => (
              <GlassCard key={v.encounter_id} style={styles.visitCard}>
                <View style={styles.visitHeader}>
                  <View style={styles.visitDateBadge}>
                    <MaterialCommunityIcons name="calendar" size={13} color={Colors.blue} />
                    <Text style={styles.visitDate}>{v.date}</Text>
                  </View>
                  <Text style={styles.encounterId}>{v.encounter_id}</Text>
                </View>
                <Text style={styles.visitSymptoms}>
                  {v.symptoms.charAt(0).toUpperCase() + v.symptoms.slice(1)}
                </Text>
                {(v.temp != null || v.heart_rate != null) && (
                  <View style={styles.vitalsRow}>
                    {v.temp != null && (
                      <View style={styles.vitalChip}>
                        <MaterialCommunityIcons name="thermometer" size={12} color={Colors.amber} />
                        <Text style={styles.vitalChipText}>{v.temp}°C</Text>
                      </View>
                    )}
                    {v.heart_rate != null && (
                      <View style={styles.vitalChip}>
                        <MaterialCommunityIcons name="heart-pulse" size={12} color={Colors.red} />
                        <Text style={styles.vitalChipText}>{v.heart_rate} bpm</Text>
                      </View>
                    )}
                  </View>
                )}
              </GlassCard>
            ))}
          </View>
        )}

        {/* ── CONDITIONS ── */}
        {tab === 'conditions' && (
          <View style={{ gap: Spacing.sm }}>
            {conditions.length === 0 ? (
              <Text style={styles.emptyText}>No conditions on record.</Text>
            ) : (
              <>
                {conditions.filter(c => c.is_active).length > 0 && (
                  <>
                    <Text style={styles.subSectionTitle}>Active</Text>
                    {conditions.filter(c => c.is_active).map((c, i) => (
                      <GlassCard key={i} style={[styles.conditionCard, { borderColor: `${Colors.red}33` }]}>
                        <View style={styles.conditionRow}>
                          <View style={[styles.conditionDot, { backgroundColor: Colors.red }]} />
                          <View style={{ flex: 1 }}>
                            <Text style={styles.conditionName}>{c.name}</Text>
                            <Text style={styles.conditionFlag}>{c.flag.replace(/_/g, ' ')}</Text>
                          </View>
                          <View style={styles.activeBadge}>
                            <Text style={styles.activeBadgeText}>ACTIVE</Text>
                          </View>
                        </View>
                      </GlassCard>
                    ))}
                  </>
                )}
                {conditions.filter(c => !c.is_active).length > 0 && (
                  <>
                    <Text style={[styles.subSectionTitle, { marginTop: Spacing.sm }]}>Past / Resolved</Text>
                    {conditions.filter(c => !c.is_active).map((c, i) => (
                      <GlassCard key={i} style={styles.conditionCard}>
                        <View style={styles.conditionRow}>
                          <View style={[styles.conditionDot, { backgroundColor: Colors.gray400 }]} />
                          <View style={{ flex: 1 }}>
                            <Text style={[styles.conditionName, { color: Colors.gray400 }]}>{c.name}</Text>
                            <Text style={styles.conditionFlag}>{c.flag.replace(/_/g, ' ')}</Text>
                          </View>
                          <View style={[styles.activeBadge, { backgroundColor: `${Colors.gray400}18`, borderColor: `${Colors.gray400}44` }]}>
                            <Text style={[styles.activeBadgeText, { color: Colors.gray400 }]}>RESOLVED</Text>
                          </View>
                        </View>
                      </GlassCard>
                    ))}
                  </>
                )}
              </>
            )}
          </View>
        )}

        {/* ── VITALS ── */}
        {tab === 'vitals' && (
          <View style={{ gap: Spacing.sm }}>
            <GlassCard>
              <View style={styles.sectionHeader}>
                <MaterialCommunityIcons name="heart-pulse" size={16} color={Colors.red} />
                <Text style={styles.sectionTitle}>Heart Rate History</Text>
              </View>
              {visits.filter(v => v.heart_rate != null).slice(0, 8).map((v, i, arr) => (
                <View key={i}>
                  <View style={styles.vitalHistRow}>
                    <Text style={styles.vitalHistDate}>{v.date}</Text>
                    <View style={styles.vitalBar}>
                      <View style={[styles.vitalBarFill, {
                        width: `${Math.min(100, ((v.heart_rate ?? 60) / 160) * 100)}%` as any,
                        backgroundColor: (v.heart_rate ?? 0) > 100 ? Colors.red : Colors.teal,
                      }]} />
                    </View>
                    <Text style={styles.vitalHistVal}>{v.heart_rate} bpm</Text>
                  </View>
                  {i < arr.length - 1 && <Divider style={{ marginVertical: 4 }} />}
                </View>
              ))}
              {visits.filter(v => v.heart_rate != null).length === 0 && (
                <Text style={styles.emptyText}>No heart rate records.</Text>
              )}
            </GlassCard>

            <GlassCard>
              <View style={styles.sectionHeader}>
                <MaterialCommunityIcons name="thermometer" size={16} color={Colors.amber} />
                <Text style={styles.sectionTitle}>Temperature History</Text>
              </View>
              {visits.filter(v => v.temp != null).slice(0, 8).map((v, i, arr) => (
                <View key={i}>
                  <View style={styles.vitalHistRow}>
                    <Text style={styles.vitalHistDate}>{v.date}</Text>
                    <View style={styles.vitalBar}>
                      <View style={[styles.vitalBarFill, {
                        width: `${Math.min(100, (((v.temp ?? 37) - 35) / 5) * 100)}%` as any,
                        backgroundColor: (v.temp ?? 37) > 37.5 ? Colors.amber : Colors.green,
                      }]} />
                    </View>
                    <Text style={styles.vitalHistVal}>{v.temp}°C</Text>
                  </View>
                  {i < arr.length - 1 && <Divider style={{ marginVertical: 4 }} />}
                </View>
              ))}
              {visits.filter(v => v.temp != null).length === 0 && (
                <Text style={styles.emptyText}>No temperature records.</Text>
              )}
            </GlassCard>
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  patientBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, margin: Spacing.lg, marginBottom: 0 },
  avatarCircle: { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: Colors.navy, fontWeight: '900', fontSize: 18 },
  patientName: { color: Colors.white, fontSize: 17, fontWeight: '800' },
  patientMeta: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  patientId: { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  tabRow: { flexDirection: 'row', paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, gap: Spacing.xs, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, paddingVertical: Spacing.xs + 2, borderRadius: Radius.sm, backgroundColor: Colors.navyMid },
  tabActive: { backgroundColor: Colors.tealDim },
  tabText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  tabTextActive: { color: Colors.teal },
  scroll: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  emptyText: { color: Colors.gray400, fontSize: 13, textAlign: 'center', paddingVertical: Spacing.xl },
  visitCard: { gap: Spacing.sm },
  visitHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  visitDateBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.blue}18`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  visitDate: { color: Colors.blue, fontSize: 12, fontWeight: '600' },
  encounterId: { color: Colors.gray600, fontSize: 11 },
  visitSymptoms: { color: Colors.white, fontSize: 14, fontWeight: '600', lineHeight: 20 },
  vitalsRow: { flexDirection: 'row', gap: Spacing.xs, flexWrap: 'wrap' },
  vitalChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  vitalChipText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  subSectionTitle: { color: Colors.gray400, fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  conditionCard: { gap: Spacing.xs },
  conditionRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  conditionDot: { width: 8, height: 8, borderRadius: 4 },
  conditionName: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  conditionFlag: { color: Colors.gray400, fontSize: 12, textTransform: 'capitalize' },
  activeBadge: { backgroundColor: `${Colors.red}18`, borderWidth: 1, borderColor: `${Colors.red}44`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  activeBadgeText: { color: Colors.red, fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.sm },
  sectionTitle: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  vitalHistRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  vitalHistDate: { color: Colors.gray600, fontSize: 11, width: 80 },
  vitalBar: { flex: 1, height: 6, backgroundColor: Colors.navyLight, borderRadius: Radius.full, overflow: 'hidden' },
  vitalBarFill: { height: '100%', borderRadius: Radius.full },
  vitalHistVal: { color: Colors.white, fontSize: 12, fontWeight: '700', width: 58, textAlign: 'right' },
});
