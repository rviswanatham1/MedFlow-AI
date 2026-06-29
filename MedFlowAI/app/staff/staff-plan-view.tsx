import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, SafeAreaView, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard } from '../../components/ui';
import { api, CarePlan } from '../../services/api';

const URGENCY_COLOR = { STAT: Colors.red, ASAP: Colors.amber, Routine: Colors.green } as const;

export default function StaffPlanViewScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const [plan, setPlan] = useState<CarePlan | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.getCarePlan(id).then(setPlan).catch(() => setPlan({ exists: false })).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator color={Colors.teal} size="large" />
    </SafeAreaView>
  );

  if (!plan?.exists) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Care Plan</Text>
        <View style={{ width: 40 }} />
      </View>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.md, padding: Spacing.xl }}>
        <MaterialCommunityIcons name="clock-outline" size={52} color={Colors.amber} />
        <Text style={{ color: Colors.white, fontSize: 18, fontWeight: '800', textAlign: 'center' }}>No Care Plan Yet</Text>
        <Text style={{ color: Colors.gray400, fontSize: 14, textAlign: 'center', lineHeight: 21 }}>The doctor has not yet created a care plan for this patient.</Text>
      </View>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <View style={{ alignItems: 'center' }}>
          <Text style={styles.headerTitle}>Care Plan</Text>
          <Text style={styles.headerSub}>{id} · For System Entry</Text>
        </View>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* System entry banner */}
        <View style={styles.epicBanner}>
          <MaterialCommunityIcons name="hospital-building" size={18} color={Colors.blue} />
          <View style={{ flex: 1 }}>
            <Text style={styles.epicTitle}>Enter into Epic / SIS</Text>
            <Text style={styles.epicSub}>Doctor-approved. Please enter all orders into the hospital system.</Text>
          </View>
        </View>

        {/* Approved stamp */}
        <GlassCard style={styles.approvedCard}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.md }}>
            <View style={styles.checkCircle}>
              <MaterialCommunityIcons name="check-bold" size={20} color={Colors.navy} />
            </View>
            <View>
              <Text style={styles.approvedTitle}>Approved by Dr. {plan.doctor_id}</Text>
              <Text style={styles.approvedSub}>{plan.approved_at ? new Date(plan.approved_at).toLocaleString() : ''}</Text>
            </View>
          </View>
        </GlassCard>

        {/* Labs */}
        {plan.labs && plan.labs.length > 0 && (
          <GlassCard>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="test-tube" size={15} color={Colors.amber} />
              <Text style={styles.sectionTitle}>Labs & Tests</Text>
              <Text style={styles.entryHint}>Enter in Order Management</Text>
            </View>
            {plan.labs.map((lab, i) => (
              <View key={i} style={styles.orderRow}>
                <View style={styles.orderLeft}>
                  <View style={[styles.urgencyBadge, { backgroundColor: `${URGENCY_COLOR[lab.urgency as keyof typeof URGENCY_COLOR] ?? Colors.green}20`, borderColor: `${URGENCY_COLOR[lab.urgency as keyof typeof URGENCY_COLOR] ?? Colors.green}44` }]}>
                    <Text style={[styles.urgencyText, { color: URGENCY_COLOR[lab.urgency as keyof typeof URGENCY_COLOR] ?? Colors.green }]}>{lab.urgency}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.orderName}>{lab.name}</Text>
                    {!!lab.timing && <Text style={styles.orderDetail}>{lab.timing}</Text>}
                  </View>
                </View>
              </View>
            ))}
          </GlassCard>
        )}

        {/* Medications */}
        {plan.medications && plan.medications.length > 0 && (
          <GlassCard>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="pill" size={15} color={Colors.teal} />
              <Text style={styles.sectionTitle}>Medications</Text>
              <Text style={styles.entryHint}>Enter in MAR / eRx</Text>
            </View>
            {plan.medications.map((med, i) => (
              <View key={i} style={[styles.medRow, i < plan.medications!.length - 1 && styles.medRowBorder]}>
                <Text style={styles.medName}>{med.name}</Text>
                <View style={styles.medDetails}>
                  <View style={styles.medChip}><Text style={styles.medChipText}>{med.dose}</Text></View>
                  <View style={styles.medChip}><Text style={styles.medChipText}>{med.frequency}</Text></View>
                  <View style={[styles.medChip, { backgroundColor: `${Colors.blue}18`, borderColor: `${Colors.blue}33` }]}>
                    <Text style={[styles.medChipText, { color: Colors.blue }]}>{med.route}</Text>
                  </View>
                </View>
                {!!med.duration && <Text style={styles.medExtra}>Duration: {med.duration}</Text>}
                {!!med.notes && <Text style={styles.medExtra}>{med.notes}</Text>}
              </View>
            ))}
          </GlassCard>
        )}

        {/* Instructions */}
        {!!plan.instructions && (
          <GlassCard>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="clipboard-text-outline" size={15} color={Colors.blue} />
              <Text style={styles.sectionTitle}>Patient Instructions</Text>
            </View>
            <Text style={styles.bodyText}>{plan.instructions}</Text>
          </GlassCard>
        )}

        {/* Follow-up */}
        {!!plan.follow_up && (
          <GlassCard>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="calendar-check-outline" size={15} color={Colors.green} />
              <Text style={styles.sectionTitle}>Follow-Up</Text>
              <Text style={styles.entryHint}>Schedule in Appointments</Text>
            </View>
            <Text style={styles.bodyText}>{plan.follow_up}</Text>
          </GlassCard>
        )}

        {/* Diet & Activity */}
        {(!!plan.diet || !!plan.activity) && (
          <GlassCard>
            <View style={styles.sectionHeader}>
              <MaterialCommunityIcons name="heart-outline" size={15} color={Colors.green} />
              <Text style={styles.sectionTitle}>Restrictions</Text>
            </View>
            {!!plan.diet && (
              <View style={styles.restrictRow}>
                <Text style={styles.restrictLabel}>Diet:</Text>
                <Text style={styles.restrictValue}>{plan.diet}</Text>
              </View>
            )}
            {!!plan.activity && (
              <View style={styles.restrictRow}>
                <Text style={styles.restrictLabel}>Activity:</Text>
                <Text style={styles.restrictValue}>{plan.activity}</Text>
              </View>
            )}
          </GlassCard>
        )}

        <View style={styles.completedNote}>
          <MaterialCommunityIcons name="information-outline" size={14} color={Colors.gray600} />
          <Text style={styles.completedNoteText}>
            Once entered in Epic/SIS, mark as completed in your worklist. This plan has also been shared with the patient.
          </Text>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  iconBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  headerSub: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  epicBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.blue}14`, borderWidth: 1, borderColor: `${Colors.blue}30`, borderRadius: Radius.md, padding: Spacing.md },
  epicTitle: { color: Colors.blue, fontSize: 13, fontWeight: '700' },
  epicSub: { color: Colors.gray400, fontSize: 11, marginTop: 2 },
  approvedCard: { borderColor: `${Colors.teal}33`, borderWidth: 1 },
  checkCircle: { width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  approvedTitle: { color: Colors.white, fontSize: 15, fontWeight: '800' },
  approvedSub: { color: Colors.gray400, fontSize: 11, marginTop: 2 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.sm },
  sectionTitle: { color: Colors.white, fontSize: 14, fontWeight: '700', flex: 1 },
  entryHint: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  orderRow: { marginBottom: Spacing.sm },
  orderLeft: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  urgencyBadge: { borderWidth: 1, borderRadius: Radius.sm, paddingHorizontal: 8, paddingVertical: 3, marginTop: 1 },
  urgencyText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  orderName: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  orderDetail: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  medRow: { paddingVertical: Spacing.sm, gap: 6 },
  medRowBorder: { borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  medName: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  medDetails: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  medChip: { backgroundColor: `${Colors.teal}18`, borderWidth: 1, borderColor: `${Colors.teal}33`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3 },
  medChipText: { color: Colors.teal, fontSize: 11, fontWeight: '700' },
  medExtra: { color: Colors.gray400, fontSize: 12 },
  bodyText: { color: Colors.gray400, fontSize: 13, lineHeight: 21 },
  restrictRow: { flexDirection: 'row', gap: Spacing.sm, marginBottom: 4 },
  restrictLabel: { color: Colors.gray400, fontSize: 13, fontWeight: '700', width: 64 },
  restrictValue: { color: Colors.white, fontSize: 13, flex: 1 },
  completedNote: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'flex-start', padding: Spacing.md, backgroundColor: Colors.navyMid, borderRadius: Radius.md },
  completedNoteText: { color: Colors.gray600, fontSize: 11, lineHeight: 17, flex: 1 },
});
