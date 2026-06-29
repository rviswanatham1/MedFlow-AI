import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, SafeAreaView, ActivityIndicator, RefreshControl, ScrollView } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, UrgencyIndicator, ConfidenceBar, Badge } from '../../components/ui';
import { api, QueueEntry } from '../../services/api';
import { useApp } from '../../context/AppContext';

const DEPARTMENTS = [
  { name: 'Emergency',    wait: 45, load: 92, patients: 14, color: Colors.red   },
  { name: 'Urgent Care',  wait: 18, load: 68, patients: 8,  color: Colors.amber },
  { name: 'Primary Care', wait: 12, load: 45, patients: 5,  color: Colors.green },
  { name: 'Radiology',    wait: 30, load: 75, patients: 6,  color: Colors.blue  },
];

const STATUS_CFG: Record<string, { label: string; color: string }> = {
  escalated:      { label: 'ESCALATED',     color: Colors.red },
  waiting:        { label: 'WAITING',        color: Colors.amber },
  pending_review: { label: 'PENDING REVIEW', color: Colors.amber },
  approved:       { label: 'APPROVED',       color: Colors.green },
};

type Filter = 'active' | 'critical' | 'pending_review' | 'approved';

export default function PatientQueueScreen() {
  const router = useRouter();
  const { isDoctor } = useApp();
  const [filter, setFilter] = useState<Filter>('active');
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadQueue = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await api.getQueue();
      setQueue(data);
    } catch {}
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  // Reload every time this screen comes into focus (after approving a patient)
  useFocusEffect(useCallback(() => { loadQueue(); }, [loadQueue]));

  const onRefresh = () => { setRefreshing(true); loadQueue(true); };

  const active = queue.filter(p => p.status !== 'approved');
  const filtered =
    filter === 'active'        ? active :
    filter === 'critical'      ? active.filter(p => p.urgency === 'critical' || p.urgency === 'high') :
    filter === 'pending_review'? active.filter(p => p.status === 'pending_review') :
    /* approved */               queue.filter(p => p.status === 'approved');

  const renderItem = ({ item: p }: { item: QueueEntry }) => {
    const st = STATUS_CFG[p.status] || STATUS_CFG.waiting;
    return (
      <TouchableOpacity onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: p.patient_id } })}>
        <GlassCard style={[styles.card, p.urgency === 'critical' && styles.cardCritical]}>
          <View style={styles.cardTop}>
            <View style={styles.cardIdRow}>
              <Text style={styles.cardId}>{p.patient_id}</Text>
              {p.age != null && <Badge label={`${p.age}y ${p.gender ?? ''}`} />}
              <View style={[styles.statusChip, { backgroundColor: `${st.color}18`, borderColor: `${st.color}44` }]}>
                <Text style={[styles.statusText, { color: st.color }]}>{st.label}</Text>
              </View>
            </View>
            <UrgencyIndicator level={p.urgency as any} />
          </View>

          {p.summary ? <Text style={styles.summary}>{p.summary}</Text> : null}

          <View style={styles.metaRow}>
            <View style={styles.pathwayChip}>
              <MaterialCommunityIcons name="source-fork" size={11} color={Colors.blue} />
              <Text style={styles.pathwayText}>{p.pathway}</Text>
            </View>
            <Text style={[styles.waitText, p.wait === 0 && { color: Colors.red }]}>
              {p.wait === 0 ? 'IMMEDIATE' : `${p.wait}m`}
            </Text>
          </View>

          {p.confidence != null && <ConfidenceBar score={p.confidence} label="AI Confidence" />}

          {p.flag && (
            <View style={[styles.flagRow, { borderColor: p.urgency === 'critical' ? `${Colors.red}40` : `${Colors.teal}30` }]}>
              <MaterialCommunityIcons name={p.urgency === 'critical' ? 'alert-circle-outline' : 'information-outline'} size={13} color={p.urgency === 'critical' ? Colors.red : Colors.teal} />
              <Text style={[styles.flagText, { color: p.urgency === 'critical' ? Colors.red : Colors.teal }]}>{p.flag}</Text>
            </View>
          )}

          <View style={styles.actions}>
            {isDoctor && p.status === 'pending_review' && (
              <TouchableOpacity style={styles.approveBtn} onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: p.patient_id } })}>
                <MaterialCommunityIcons name="check" size={14} color={Colors.navy} />
                <Text style={styles.approveBtnText}>Approve</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity style={styles.reviewBtn} onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: p.patient_id } })}>
              <Text style={styles.reviewBtnText}>Full Review →</Text>
            </TouchableOpacity>
          </View>
        </GlassCard>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Patient Queue</Text>
          <Text style={styles.headerCount}>
            {active.length} active · {queue.filter(p => p.status === 'pending_review').length} pending review
          </Text>
        </View>
        <TouchableOpacity style={styles.backBtn} onPress={() => loadQueue(true)}>
          <MaterialCommunityIcons name="refresh" size={22} color={Colors.teal} />
        </TouchableOpacity>
      </View>

      <View style={styles.filterRow}>
        {([
          { key: 'active',         label: 'Active',       count: active.length },
          { key: 'critical',       label: 'Critical',     count: active.filter(p => p.urgency === 'critical' || p.urgency === 'high').length },
          { key: 'pending_review', label: 'Pending',      count: active.filter(p => p.status === 'pending_review').length },
          { key: 'approved',       label: 'Done',         count: queue.filter(p => p.status === 'approved').length },
        ] as { key: Filter; label: string; count: number }[]).map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterChip, filter === f.key && styles.filterChipActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[styles.filterText, filter === f.key && styles.filterTextActive]}>{f.label}</Text>
            {f.count > 0 && (
              <View style={[styles.filterBadge, filter === f.key && styles.filterBadgeActive]}>
                <Text style={[styles.filterBadgeText, filter === f.key && { color: Colors.teal }]}>{f.count}</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* Department Status */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.deptScroll} contentContainerStyle={styles.deptScrollContent}>
        {DEPARTMENTS.map(dept => (
          <View key={dept.name} style={styles.deptCard}>
            <Text style={styles.deptName}>{dept.name}</Text>
            <Text style={[styles.deptWait, { color: dept.color }]}>{dept.wait}m</Text>
            <Text style={styles.deptPatients}>{dept.patients} active</Text>
            <View style={styles.loadTrack}>
              <View style={[styles.loadFill, { width: `${dept.load}%` as any, backgroundColor: dept.color }]} />
            </View>
            <Text style={[styles.loadPct, { color: dept.color }]}>{dept.load}%</Text>
          </View>
        ))}
      </ScrollView>

      {loading ? (
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator color={Colors.teal} size="large" />
          <Text style={{ color: Colors.gray400, marginTop: Spacing.md }}>Loading queue…</Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={item => item.patient_id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.teal} />}
          ListEmptyComponent={
            <View style={{ alignItems: 'center', padding: Spacing.xl, gap: Spacing.md }}>
              <MaterialCommunityIcons
                name={filter === 'approved' ? 'check-circle-outline' : 'clipboard-text-outline'}
                size={48}
                color={filter === 'approved' ? Colors.teal : Colors.gray600}
              />
              <Text style={{ color: Colors.gray400, textAlign: 'center', fontSize: 14 }}>
                {filter === 'approved'
                  ? 'No approved patients yet.'
                  : 'No active patients in queue.\nPull down to refresh.'}
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  headerCount: { color: Colors.white, fontSize: 11, marginTop: 1, opacity: 0.6 },
  filterRow: { flexDirection: 'row', padding: Spacing.md, gap: Spacing.xs, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  filterChip: { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full },
  filterChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  filterText: { color: Colors.gray400, fontSize: 12 },
  filterTextActive: { color: Colors.teal, fontWeight: '700' },
  deptScroll: { borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  deptScrollContent: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, gap: Spacing.sm },
  deptCard: { backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.sm, gap: 3, width: 110 },
  deptName: { color: Colors.white, fontSize: 11, fontWeight: '700' },
  deptWait: { fontSize: 20, fontWeight: '900', letterSpacing: -0.5 },
  deptPatients: { color: Colors.gray600, fontSize: 10 },
  loadTrack: { height: 4, backgroundColor: Colors.navyLight, borderRadius: Radius.full, overflow: 'hidden', marginTop: 2 },
  loadFill: { height: '100%', borderRadius: Radius.full },
  loadPct: { fontSize: 10, fontWeight: '700' },
  filterBadge: { backgroundColor: Colors.navyLight, borderRadius: 8, paddingHorizontal: 5, paddingVertical: 1 },
  filterBadgeActive: { backgroundColor: `${Colors.teal}22` },
  filterBadgeText: { color: Colors.gray600, fontSize: 10, fontWeight: '700' },
  list: { padding: Spacing.md, gap: Spacing.sm, paddingBottom: Spacing.xxl },
  card: { gap: Spacing.sm },
  cardCritical: { borderColor: `${Colors.red}55`, backgroundColor: `${Colors.red}06` },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  cardIdRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, flexWrap: 'wrap', flex: 1, marginRight: Spacing.sm },
  cardId: { color: Colors.white, fontSize: 16, fontWeight: '800' },
  statusChip: { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  statusText: { fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },
  summary: { color: Colors.gray400, fontSize: 13, lineHeight: 18 },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  pathwayChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.blue}18`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  pathwayText: { color: Colors.blue, fontSize: 11, fontWeight: '600' },
  waitText: { color: Colors.amber, fontSize: 12, fontWeight: '700' },
  flagRow: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: Colors.navyLight, borderWidth: 1, borderRadius: Radius.sm, padding: Spacing.xs + 2 },
  flagText: { fontSize: 11, flex: 1, lineHeight: 15 },
  actions: { flexDirection: 'row', gap: Spacing.sm },
  approveBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.teal, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  approveBtnText: { color: Colors.navy, fontWeight: '700', fontSize: 12 },
  reviewBtn: { flex: 1, alignItems: 'center', borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingVertical: Spacing.xs },
  reviewBtnText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
});
