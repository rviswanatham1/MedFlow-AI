import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Dimensions, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, SectionHeader } from '../../components/ui';

const { width } = Dimensions.get('window');

const HOURLY = [
  {h:'8A',a:12,p:11},{h:'9A',a:18,p:17},{h:'10A',a:22,p:24},{h:'11A',a:28,p:26},
  {h:'12P',a:31,p:30},{h:'1P',a:27,p:29},{h:'2P',a:34,p:38},
  {h:'3P',a:null,p:42},{h:'4P',a:null,p:45},{h:'5P',a:null,p:38},{h:'6P',a:null,p:30},
];
const MAX_V = 50;

const STAFFING = [
  { time: '2–5 PM', action: 'Add 2 nursing staff',        urgency: 'high',   dept: 'Emergency' },
  { time: '3–6 PM', action: 'Open overflow bay 3',        urgency: 'medium', dept: 'Urgent Care' },
  { time: '5–7 PM', action: 'Extend Dr. Williams shift',  urgency: 'low',    dept: 'Primary Care' },
];

const urgColor = (u: string) => u === 'high' ? Colors.red : u === 'medium' ? Colors.amber : Colors.green;

export default function AnalyticsScreen() {
  const router  = useRouter();
  const CHART_H = 130;
  const barH = (v: number) => (v / MAX_V) * CHART_H;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>AI Analytics</Text>
        <View style={styles.liveChip}><View style={styles.liveDot} /><Text style={styles.liveText}>LIVE</Text></View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* KPIs */}
        <View style={styles.kpiGrid}>
          {[
            { label: 'Avg Triage Time', val: '4.2m', delta: '−1.1m', good: true },
            { label: 'No-Show Rate',    val: '8.4%', delta: '−2.1%', good: true },
            { label: 'AI Accuracy',     val: '91%',  delta: '+3%',   good: true },
            { label: 'Escalations',     val: '2',    delta: '−1',    good: true },
          ].map(k => (
            <GlassCard key={k.label} style={styles.kpiCard}>
              <Text style={styles.kpiVal}>{k.val}</Text>
              <Text style={styles.kpiLabel}>{k.label}</Text>
              <Text style={[styles.kpiDelta, { color: k.good ? Colors.green : Colors.red }]}>{k.delta}</Text>
            </GlassCard>
          ))}
        </View>

        {/* Volume chart */}
        <GlassCard>
          <SectionHeader title="Patient Volume Forecast" />
          <View style={styles.legend}>
            <View style={styles.legendItem}><View style={[styles.legendDot, { backgroundColor: Colors.teal }]} /><Text style={styles.legendText}>Actual</Text></View>
            <View style={styles.legendItem}><View style={[styles.legendDot, { backgroundColor: `${Colors.blue}66` }]} /><Text style={styles.legendText}>Predicted</Text></View>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={[styles.chartBars, { height: CHART_H + 28 }]}>
              {HOURLY.map(d => (
                <View key={d.h} style={styles.barCol}>
                  <View style={[styles.barStack, { height: CHART_H }]}>
                    <View style={[styles.barPred, { height: barH(d.p) }]} />
                    {d.a !== null && <View style={[styles.barActual, { height: barH(d.a) }]} />}
                  </View>
                  <Text style={styles.barLbl}>{d.h}</Text>
                  {d.a === null && <Text style={styles.estLbl}>est</Text>}
                </View>
              ))}
            </View>
          </ScrollView>
          <View style={styles.peakWarn}>
            <MaterialCommunityIcons name="alert-outline" size={14} color={Colors.amber} />
            <Text style={styles.peakWarnText}>Peak of 45 patients predicted at 4 PM — staffing action recommended.</Text>
          </View>
        </GlassCard>

        {/* Staffing recs */}
        <GlassCard>
          <SectionHeader title="Staffing Recommendations" />
          {STAFFING.map((s, i) => (
            <View key={i} style={styles.staffRow}>
              <View style={[styles.staffDot, { backgroundColor: urgColor(s.urgency) }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.staffAction}>{s.action}</Text>
                <Text style={styles.staffMeta}>{s.time} · {s.dept}</Text>
              </View>
              <TouchableOpacity style={styles.applyBtn}><Text style={styles.applyBtnText}>Apply</Text></TouchableOpacity>
            </View>
          ))}
        </GlassCard>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  liveChip: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.red}18`, borderWidth: 1, borderColor: `${Colors.red}44`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.red },
  liveText: { color: Colors.red, fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  kpiCard: { width: (width - Spacing.lg * 2 - Spacing.sm) / 2, gap: 2 },
  kpiVal: { color: Colors.white, fontSize: 24, fontWeight: '900', marginTop: 4 },
  kpiLabel: { color: Colors.gray400, fontSize: 12 },
  kpiDelta: { fontSize: 11, fontWeight: '600', marginTop: 2 },
  legend: { flexDirection: 'row', gap: Spacing.md, marginBottom: Spacing.md },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: Colors.gray400, fontSize: 12 },
  chartBars: { flexDirection: 'row', alignItems: 'flex-end', gap: 10, paddingBottom: 4 },
  barCol: { alignItems: 'center', width: 28 },
  barStack: { width: '100%', position: 'relative', justifyContent: 'flex-end' },
  barPred: { width: '100%', backgroundColor: `${Colors.blue}44`, borderRadius: 3, position: 'absolute', bottom: 0 },
  barActual: { width: '60%', backgroundColor: Colors.teal, borderRadius: 3, position: 'absolute', bottom: 0, left: '20%' },
  barLbl: { color: Colors.gray600, fontSize: 8, marginTop: 4, textAlign: 'center' },
  estLbl: { color: `${Colors.blue}88`, fontSize: 7 },
  peakWarn: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: `${Colors.amber}10`, borderRadius: Radius.sm, padding: Spacing.xs + 2, marginTop: Spacing.sm },
  peakWarnText: { color: Colors.amber, fontSize: 12, flex: 1, lineHeight: 16 },
  staffRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, marginBottom: Spacing.md },
  staffDot: { width: 8, height: 8, borderRadius: 4 },
  staffAction: { color: Colors.white, fontSize: 13, fontWeight: '600' },
  staffMeta: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  applyBtn: { backgroundColor: Colors.tealDim, borderWidth: 1, borderColor: `${Colors.teal}44`, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  applyBtnText: { color: Colors.teal, fontSize: 12, fontWeight: '700' },
});
