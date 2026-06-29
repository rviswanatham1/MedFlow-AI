import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Button, Divider } from '../../components/ui';

// TODO: GET /api/price/estimate { cpt_codes[], insurance_id, provider_id }
// TODO: GET /api/insurance/benefits { member_id } → deductible, OOP, copay
// Source: CMS Price Transparency MRF + hospital chargemaster + Availity eligibility

const ESTIMATE = {
  visitType: 'Urgent Care Visit',
  provider: 'Dr. Priya Patel',
  cptCodes: [
    { code: '99213', description: 'Office/outpatient visit',         chargemaster: 285, negotiated: 142 },
    { code: '93000', description: 'ECG with interpretation',         chargemaster: 180, negotiated: 74  },
  ],
  insurance: {
    plan: 'Blue Cross Blue Shield PPO',
    deductible: { total: 1500, met: 840 },
    outOfPocketMax: { total: 4000, met: 840 },
    coinsurance: 20,
    copay: 30,
  },
};

const deductibleLeft   = ESTIMATE.insurance.deductible.total - ESTIMATE.insurance.deductible.met;
const totalNegotiated  = ESTIMATE.cptCodes.reduce((s, c) => s + c.negotiated, 0);
const deductiblePct    = (ESTIMATE.insurance.deductible.met / ESTIMATE.insurance.deductible.total) * 100;
const oopPct           = (ESTIMATE.insurance.outOfPocketMax.met / ESTIMATE.insurance.outOfPocketMax.total) * 100;

export default function PriceEstimateScreen() {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Price Estimate</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* Hero copay */}
        <GlassCard style={styles.heroCard} glow>
          <Text style={styles.heroLabel}>YOUR ESTIMATED COST</Text>
          <Text style={styles.heroAmount}>${ESTIMATE.insurance.copay}</Text>
          <Text style={styles.heroCopayLabel}>Copay</Text>
          <View style={styles.heroDivider} />
          <View style={styles.heroMeta}>
            <View style={styles.heroMetaItem}>
              <MaterialCommunityIcons name="shield-check" size={13} color={Colors.green} />
              <Text style={styles.heroMetaText}>{ESTIMATE.insurance.plan}</Text>
            </View>
            <View style={styles.heroMetaItem}>
              <MaterialCommunityIcons name="hospital-building" size={13} color={Colors.gray400} />
              <Text style={styles.heroMetaText}>{ESTIMATE.visitType}</Text>
            </View>
          </View>
          <View style={styles.disclaimerBox}>
            <MaterialCommunityIcons name="information-outline" size={12} color={Colors.amber} />
            <Text style={styles.disclaimerText}>Estimate only. Final cost may vary based on services rendered.</Text>
          </View>
        </GlassCard>

        {/* Benefits */}
        <GlassCard style={styles.benefitsCard}>
          <View style={styles.cardHeader}>
            <MaterialCommunityIcons name="card-account-details-outline" size={16} color={Colors.blue} />
            <Text style={styles.cardTitle}>Your Benefits</Text>
          </View>

          <Text style={styles.benefitLabel}>Deductible</Text>
          <View style={styles.benefitRow}>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${deductiblePct}%` as any, backgroundColor: Colors.blue }]} />
            </View>
            <Text style={styles.benefitAmt}>${ESTIMATE.insurance.deductible.met} / ${ESTIMATE.insurance.deductible.total}</Text>
          </View>
          <Text style={styles.benefitSub}>${deductibleLeft} remaining</Text>

          <Divider />

          <Text style={styles.benefitLabel}>Out-of-Pocket Max</Text>
          <View style={styles.benefitRow}>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${oopPct}%` as any, backgroundColor: Colors.teal }]} />
            </View>
            <Text style={styles.benefitAmt}>${ESTIMATE.insurance.outOfPocketMax.met} / ${ESTIMATE.insurance.outOfPocketMax.total}</Text>
          </View>
          <Text style={styles.benefitSub}>${ESTIMATE.insurance.outOfPocketMax.total - ESTIMATE.insurance.outOfPocketMax.met} remaining</Text>

          <Divider />

          <View style={styles.costShareRow}>
            <View style={styles.costShareItem}>
              <Text style={styles.costShareVal}>${ESTIMATE.insurance.copay}</Text>
              <Text style={styles.costShareLabel}>Copay</Text>
            </View>
            <View style={styles.costShareDivider} />
            <View style={styles.costShareItem}>
              <Text style={styles.costShareVal}>{ESTIMATE.insurance.coinsurance}%</Text>
              <Text style={styles.costShareLabel}>Coinsurance</Text>
            </View>
            <View style={styles.costShareDivider} />
            <View style={styles.costShareItem}>
              <Text style={[styles.costShareVal, { color: Colors.green, fontSize: 14 }]}>In-Network</Text>
              <Text style={styles.costShareLabel}>Status</Text>
            </View>
          </View>
        </GlassCard>

        {/* Service breakdown — collapsible */}
        <GlassCard>
          <TouchableOpacity style={styles.cardHeader} onPress={() => setExpanded(!expanded)}>
            <MaterialCommunityIcons name="receipt" size={16} color={Colors.amber} />
            <Text style={styles.cardTitle}>Service Breakdown</Text>
            <MaterialCommunityIcons name={expanded ? 'chevron-up' : 'chevron-down'} size={18} color={Colors.gray400} />
          </TouchableOpacity>

          {!expanded && (
            <Text style={styles.expandHint}>{ESTIMATE.cptCodes.length} services · tap to expand</Text>
          )}

          {expanded && (
            <View style={styles.cptList}>
              {ESTIMATE.cptCodes.map((c, i) => (
                <View key={c.code}>
                  <View style={styles.cptRow}>
                    <View style={styles.cptCodeBadge}>
                      <Text style={styles.cptCodeText}>{c.code}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.cptDesc}>{c.description}</Text>
                      <View style={styles.cptPrices}>
                        <Text style={styles.cptChargemaster}>${c.chargemaster}</Text>
                        <MaterialCommunityIcons name="arrow-right" size={11} color={Colors.gray600} />
                        <Text style={styles.cptNegotiated}>${c.negotiated} negotiated</Text>
                      </View>
                    </View>
                  </View>
                  {i < ESTIMATE.cptCodes.length - 1 && <Divider />}
                </View>
              ))}
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>Total Negotiated</Text>
                <Text style={styles.totalVal}>${totalNegotiated}</Text>
              </View>
            </View>
          )}
        </GlassCard>

        <Button label="Proceed to Booking" onPress={() => router.push('/patient/book-appointment')} size="lg" style={{ width: '100%' }} />

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  heroCard: { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xl },
  heroLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '700', letterSpacing: 1.5 },
  heroAmount: { color: Colors.teal, fontSize: 72, fontWeight: '900', letterSpacing: -3, lineHeight: 78 },
  heroCopayLabel: { color: Colors.teal, fontSize: 16, fontWeight: '600', marginTop: -8 },
  heroDivider: { width: '100%', height: 1, backgroundColor: Colors.glassBorder, marginVertical: 4 },
  heroMeta: { gap: 6, alignSelf: 'stretch' },
  heroMetaItem: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  heroMetaText: { color: Colors.gray400, fontSize: 13 },
  disclaimerBox: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: `${Colors.amber}10`, borderWidth: 1, borderColor: `${Colors.amber}30`, borderRadius: Radius.sm, padding: Spacing.sm, alignSelf: 'stretch' },
  disclaimerText: { color: Colors.amber, fontSize: 11, flex: 1, lineHeight: 16 },
  benefitsCard: { gap: Spacing.sm },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.xs },
  cardTitle: { color: Colors.white, fontSize: 14, fontWeight: '700', flex: 1 },
  benefitLabel: { color: Colors.gray400, fontSize: 12, fontWeight: '600', letterSpacing: 0.5 },
  benefitRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: 5 },
  progressTrack: { flex: 1, height: 8, backgroundColor: Colors.navyLight, borderRadius: Radius.full, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: Radius.full },
  benefitAmt: { color: Colors.white, fontSize: 12, fontWeight: '700', width: 96, textAlign: 'right' },
  benefitSub: { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  costShareRow: { flexDirection: 'row', paddingTop: Spacing.xs },
  costShareItem: { flex: 1, alignItems: 'center', gap: 3 },
  costShareVal: { color: Colors.white, fontSize: 16, fontWeight: '800' },
  costShareLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  costShareDivider: { width: 1, height: 36, backgroundColor: Colors.glassBorder },
  expandHint: { color: Colors.gray600, fontSize: 12 },
  cptList: { gap: Spacing.sm, marginTop: Spacing.xs },
  cptRow: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'flex-start' },
  cptCodeBadge: { backgroundColor: Colors.navyLight, borderRadius: Radius.sm, paddingHorizontal: 8, paddingVertical: 3 },
  cptCodeText: { color: Colors.teal, fontSize: 11, fontWeight: '800' },
  cptDesc: { color: Colors.white, fontSize: 13, fontWeight: '600', marginBottom: 3 },
  cptPrices: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  cptChargemaster: { color: Colors.gray600, fontSize: 11, textDecorationLine: 'line-through' },
  cptNegotiated: { color: Colors.green, fontSize: 11, fontWeight: '700' },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.glassBorder },
  totalLabel: { color: Colors.gray400, fontSize: 13, fontWeight: '700' },
  totalVal: { color: Colors.white, fontSize: 18, fontWeight: '900' },
});
