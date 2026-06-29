import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, Animated, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';

const urgencyColor = (u: string) =>
  ({ critical: Colors.urgencyCritical, high: Colors.red, medium: Colors.amber, low: Colors.green }[u] || Colors.gray400);

export default function WaitTimeScreen() {
  const router = useRouter();
  const { patientId, triageResult } = useApp();
  const rotate = useRef(new Animated.Value(0)).current;
  const [notifEnabled, setNotifEnabled] = useState(false);
  const [myPosition, setMyPosition] = useState(triageResult?.queue_position ?? 4);
  const [myWait, setMyWait] = useState(triageResult?.estimated_wait ?? 18);

  useEffect(() => {
    Animated.loop(
      Animated.timing(rotate, { toValue: 1, duration: 4000, useNativeDriver: true })
    ).start();
    // refresh live queue status
    api.getQueueStatus(patientId)
      .then(s => { setMyPosition(s.position); setMyWait(s.wait); })
      .catch(() => {}); // keep values from triageResult on error
  }, []);

  const spin = rotate.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Queue Status</Text>
        <View style={styles.liveChip}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* ── MY POSITION HERO ── */}
        <GlassCard style={styles.heroCard} glow>
          {/* Spinning dial */}
          <View style={styles.dialWrapper}>
            <Animated.View style={[styles.dialRing, { transform: [{ rotate: spin }] }]} />
            <View style={styles.dialInner}>
              <Text style={styles.dialNum}>{myPosition}</Text>
              <Text style={styles.dialSub}>in queue</Text>
            </View>
          </View>

          {/* Wait + people ahead */}
          <View style={styles.heroStats}>
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>{myWait}</Text>
              <Text style={styles.heroStatUnit}>min</Text>
              <Text style={styles.heroStatLabel}>estimated wait</Text>
            </View>
            <View style={styles.heroStatDivider} />
            <View style={styles.heroStat}>
              <Text style={styles.heroStatVal}>{Math.max(0, myPosition - 1)}</Text>
              <Text style={styles.heroStatLabel}>people ahead of you</Text>
            </View>
          </View>

          <View style={styles.aiNote}>
            <MaterialCommunityIcons name="chip" size={12} color={Colors.teal} />
            <Text style={styles.aiNoteText}>Updates in real time</Text>
          </View>
        </GlassCard>

        {/* ── NOTIFY ME ── */}
        <TouchableOpacity
          style={[styles.notifCTA, notifEnabled && styles.notifCTAActive]}
          onPress={() => setNotifEnabled(!notifEnabled)}
        >
          <MaterialCommunityIcons
            name={notifEnabled ? 'bell-check' : 'bell-ring-outline'}
            size={20}
            color={notifEnabled ? Colors.navy : Colors.teal}
          />
          <Text style={[styles.notifCTAText, notifEnabled && styles.notifCTATextActive]}>
            {notifEnabled ? 'Notifying you when you\'re next ✓' : 'Notify me when I\'m next'}
          </Text>
        </TouchableOpacity>

        {/* ── YOUR POSITION ── */}
        <View>
          <Text style={styles.sectionTitle}>Your Position</Text>
          <GlassCard style={styles.queueCardMe}>
            <View style={[styles.urgencyStripe, { backgroundColor: Colors.teal }]} />
            <View style={styles.queueCardInner}>
              <View style={styles.youBadge}><Text style={styles.youBadgeText}>YOU</Text></View>
              <Text style={[styles.queueWait, { color: Colors.teal }]}>{myWait}m</Text>
            </View>
          </GlassCard>
        </View>


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
  scroll: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: Spacing.xxl },

  // Hero
  heroCard: { alignItems: 'center', gap: Spacing.lg, paddingVertical: Spacing.xl },
  dialWrapper: { width: 110, height: 110, alignItems: 'center', justifyContent: 'center', position: 'relative' },
  dialRing: { position: 'absolute', width: 110, height: 110, borderRadius: 55, borderWidth: 3, borderColor: Colors.teal, borderTopColor: 'transparent' },
  dialInner: { width: 88, height: 88, borderRadius: 44, backgroundColor: Colors.navyMid, alignItems: 'center', justifyContent: 'center' },
  dialNum: { color: Colors.teal, fontSize: 26, fontWeight: '900', letterSpacing: -1 },
  dialSub: { color: Colors.gray600, fontSize: 9, fontWeight: '600' },
  heroStats: { flexDirection: 'row', alignItems: 'center', width: '100%' },
  heroStat: { flex: 1, alignItems: 'center', gap: 2 },
  heroStatVal: { color: Colors.white, fontSize: 36, fontWeight: '900', letterSpacing: -1, lineHeight: 40 },
  heroStatUnit: { color: Colors.gray400, fontSize: 16, fontWeight: '600', marginTop: -4 },
  heroStatLabel: { color: Colors.gray600, fontSize: 11, fontWeight: '600', textAlign: 'center' },
  heroStatDivider: { width: 1, height: 50, backgroundColor: Colors.glassBorder },
  aiNote: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  aiNoteText: { color: Colors.gray600, fontSize: 11 },

  // Notify CTA
  notifCTA: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, backgroundColor: Colors.tealDim2, borderWidth: 1.5, borderColor: `${Colors.teal}44`, borderRadius: Radius.lg, padding: Spacing.md },
  notifCTAActive: { backgroundColor: Colors.teal, borderColor: Colors.teal },
  notifCTAText: { color: Colors.teal, fontSize: 14, fontWeight: '700' },
  notifCTATextActive: { color: Colors.navy },

  // Queue
  sectionTitle: { color: Colors.white, fontSize: 16, fontWeight: '700', marginBottom: Spacing.sm },
  queueRowWrap: { flexDirection: 'row', alignItems: 'center', marginBottom: Spacing.xs, gap: Spacing.sm },
  posNum: { width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.navyLight, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  posNumMe: { backgroundColor: Colors.teal },
  posNumText: { color: Colors.gray400, fontSize: 12, fontWeight: '800' },
  posNumTextMe: { color: Colors.navy },
  connector: { position: 'absolute', left: 13, top: 28, width: 2, height: Spacing.xs + 4, zIndex: -1 },
  queueCard: { flex: 1, flexDirection: 'row', backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, overflow: 'hidden' },
  queueCardMe: { borderColor: `${Colors.teal}55`, backgroundColor: Colors.tealDim2 },
  urgencyStripe: { width: 4 },
  queueCardInner: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.sm, paddingVertical: Spacing.sm },
  queueCardLeft: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  youBadge: { backgroundColor: Colors.teal, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 2 },
  youBadgeText: { color: Colors.navy, fontSize: 11, fontWeight: '900', letterSpacing: 1 },
  queuePosition: { color: Colors.gray400, fontSize: 13 },
  urgencyDot: { width: 7, height: 7, borderRadius: 3.5 },
  queueWait: { color: Colors.gray400, fontSize: 13, fontWeight: '700' },

});
