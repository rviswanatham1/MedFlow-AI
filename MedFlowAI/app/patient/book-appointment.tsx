import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Button, Badge } from '../../components/ui';

const PROVIDERS = [
  { id: 1, name: 'Dr. Priya Patel',   specialty: 'Internal Medicine', rating: 4.9, nextAvail: 'Tomorrow, Jun 3', slots: ['9:00 AM', '11:30 AM', '2:15 PM'] },
  { id: 2, name: 'Dr. Marcus Webb',   specialty: 'Primary Care',      rating: 4.7, nextAvail: 'Wed, Jun 4',     slots: ['10:00 AM', '3:30 PM'] },
  { id: 3, name: 'Dr. Sarah Chen',    specialty: 'Cardiology',        rating: 4.8, nextAvail: 'Thu, Jun 5',     slots: ['9:30 AM', '1:00 PM'] },
];

const VISIT_TYPES = [
  { id: 'inperson',   label: 'In-Person',   icon: 'hospital-building' },
  { id: 'urgent',     label: 'Urgent Care', icon: 'ambulance' },
];

export default function BookAppointmentScreen() {
  const router = useRouter();
  const [visitType, setVisitType] = useState('inperson');
  const [selectedProvider, setSelectedProvider] = useState<number | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  const provider = PROVIDERS.find(p => p.id === selectedProvider);

  const handleBook = () => {
    setLoading(true);
    // TODO: POST /api/appointments/book { provider_id, slot, visit_type, patient_id }
    setTimeout(() => { setLoading(false); setStep(2); }, 1500);
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => step > 0 ? setStep(s => s - 1) : router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Book a Visit</Text>
        <View style={{ width: 40 }} />
      </View>

      {/* Confirmed */}
      {step === 2 ? (
        <View style={styles.successContainer}>
          <View style={styles.successIcon}>
            <MaterialCommunityIcons name="calendar-check" size={52} color={Colors.teal} />
          </View>
          <Text style={styles.successTitle}>Appointment Confirmed</Text>
          <GlassCard style={styles.successCard}>
            {[
              { icon: 'account-outline',   val: provider?.name },
              { icon: 'medical-bag',        val: provider?.specialty },
              { icon: 'calendar-outline',  val: `${provider?.nextAvail} · ${selectedSlot}` },
              { icon: 'shield-check',      val: 'Insurance pre-verified', color: Colors.green },
            ].map((row, i) => (
              <View key={i} style={styles.successRow}>
                <MaterialCommunityIcons name={row.icon as any} size={16} color={row.color || Colors.gray400} />
                <Text style={[styles.successVal, row.color ? { color: row.color } : {}]}>{row.val}</Text>
              </View>
            ))}
          </GlassCard>
          <Button label="Back to Home" onPress={() => router.replace('/patient/home')} size="lg" style={{ width: '100%' }} />
        </View>

      ) : step === 1 && provider ? (
        /* Review */
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.stepTitle}>Review & Confirm</Text>
          <GlassCard style={styles.reviewCard}>
            <Text style={styles.reviewLabel}>PROVIDER</Text>
            <Text style={styles.reviewVal}>{provider.name}</Text>
            <Text style={styles.reviewSub}>{provider.specialty}</Text>
            <View style={styles.reviewDivider} />
            <Text style={styles.reviewLabel}>DATE & TIME</Text>
            <Text style={styles.reviewVal}>{provider.nextAvail}</Text>
            <Text style={styles.reviewSub}>{selectedSlot}</Text>
            <View style={styles.reviewDivider} />
            <Text style={styles.reviewLabel}>VISIT TYPE</Text>
            <Text style={styles.reviewVal}>{VISIT_TYPES.find(v => v.id === visitType)?.label}</Text>
            <View style={styles.reviewDivider} />
            <View style={styles.insuranceRow}>
              <MaterialCommunityIcons name="shield-check" size={16} color={Colors.green} />
              <Text style={styles.insuranceText}>Eligibility pre-verified</Text>
            </View>
          </GlassCard>
          <GlassCard>
            <Text style={styles.reviewLabel}>COPAY ESTIMATE</Text>
            <Text style={styles.copay}>$30</Text>
          </GlassCard>
          <Button label="Confirm Booking" onPress={handleBook} loading={loading} size="lg" />
          <Button label="Edit" onPress={() => setStep(0)} variant="ghost" size="md" />
        </ScrollView>

      ) : (
        /* Selection */
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Visit type */}
          <Text style={styles.sectionTitle}>Visit Type</Text>
          <View style={styles.visitTypeRow}>
            {VISIT_TYPES.map(v => (
              <TouchableOpacity
                key={v.id}
                style={[styles.visitTypeCard, visitType === v.id && styles.visitTypeCardActive]}
                onPress={() => setVisitType(v.id)}
              >
                <MaterialCommunityIcons name={v.icon as any} size={22} color={visitType === v.id ? Colors.navy : Colors.teal} />
                <Text style={[styles.visitTypeLabel, visitType === v.id && styles.visitTypeLabelActive]}>{v.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Providers */}
          <Text style={styles.sectionTitle}>Available Providers</Text>
          {PROVIDERS.map(p => (
            <TouchableOpacity key={p.id} onPress={() => setSelectedProvider(p.id)}>
              <GlassCard style={[styles.providerCard, selectedProvider === p.id && styles.providerCardActive]}>
                <View style={styles.providerHeader}>
                  <View style={styles.providerAvatar}>
                    <Text style={styles.providerAvatarText}>{p.name.split(' ').map(w => w[0]).join('')}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.providerName}>{p.name}</Text>
                    <Text style={styles.providerSpecialty}>{p.specialty}</Text>
                    <View style={styles.ratingRow}>
                      <MaterialCommunityIcons name="star" size={12} color={Colors.amber} />
                      <Text style={styles.ratingText}>{p.rating}</Text>
                    </View>
                  </View>
                  {selectedProvider === p.id && (
                    <MaterialCommunityIcons name="check-circle" size={22} color={Colors.teal} />
                  )}
                </View>
                <View style={styles.availRow}>
                  <MaterialCommunityIcons name="calendar-outline" size={14} color={Colors.gray400} />
                  <Text style={styles.availText}>Next: {p.nextAvail}</Text>
                </View>
                {selectedProvider === p.id && (
                  <View style={styles.slotsSection}>
                    <Text style={styles.slotsLabel}>SELECT TIME</Text>
                    <View style={styles.slotsRow}>
                      {p.slots.map(slot => (
                        <TouchableOpacity
                          key={slot}
                          style={[styles.slotBtn, selectedSlot === slot && styles.slotBtnActive]}
                          onPress={() => setSelectedSlot(slot)}
                        >
                          <Text style={[styles.slotText, selectedSlot === slot && styles.slotTextActive]}>{slot}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  </View>
                )}
              </GlassCard>
            </TouchableOpacity>
          ))}

          <Button label="View Price Estimate" onPress={() => router.push("/patient/price-estimate")} variant="ghost" size="md" />
          <Button label="Review Booking" onPress={() => setStep(1)} disabled={!selectedProvider || !selectedSlot} size="lg" />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  sectionTitle: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  visitTypeRow: { flexDirection: 'row', gap: Spacing.sm },
  visitTypeCard: { flex: 1, alignItems: 'center', gap: Spacing.xs, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.md },
  visitTypeCardActive: { backgroundColor: Colors.teal, borderColor: Colors.teal },
  visitTypeLabel: { color: Colors.teal, fontSize: 11, fontWeight: '700', textAlign: 'center' },
  visitTypeLabelActive: { color: Colors.navy },
  providerCard: { gap: Spacing.sm },
  providerCardActive: { borderColor: `${Colors.teal}55`, backgroundColor: Colors.tealDim2 },
  providerHeader: { flexDirection: 'row', gap: Spacing.md, alignItems: 'flex-start' },
  providerAvatar: { width: 46, height: 46, borderRadius: 23, backgroundColor: Colors.navyLight, alignItems: 'center', justifyContent: 'center' },
  providerAvatarText: { color: Colors.teal, fontWeight: '800', fontSize: 13 },
  providerName: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  providerSpecialty: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  ratingRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  ratingText: { color: Colors.amber, fontSize: 12, fontWeight: '700' },
  availRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  availText: { color: Colors.gray400, fontSize: 13 },
  slotsSection: { borderTopWidth: 1, borderTopColor: Colors.glassBorder, paddingTop: Spacing.sm, gap: Spacing.xs },
  slotsLabel: { color: Colors.gray400, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  slotsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  slotBtn: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm },
  slotBtnActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  slotText: { color: Colors.gray400, fontSize: 13 },
  slotTextActive: { color: Colors.teal, fontWeight: '700' },
  stepTitle: { color: Colors.white, fontSize: 22, fontWeight: '800' },
  reviewCard: { gap: Spacing.md },
  reviewLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  reviewVal: { color: Colors.white, fontSize: 15, fontWeight: '700', marginTop: 2 },
  reviewSub: { color: Colors.gray400, fontSize: 13, marginTop: 2 },
  reviewDivider: { height: 1, backgroundColor: Colors.glassBorder },
  insuranceRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  insuranceText: { color: Colors.green, fontSize: 14, fontWeight: '600' },
  copay: { color: Colors.teal, fontSize: 30, fontWeight: '900', marginTop: 4 },
  successContainer: { flex: 1, padding: Spacing.xl, alignItems: 'center', justifyContent: 'center', gap: Spacing.lg },
  successIcon: { width: 100, height: 100, borderRadius: 50, backgroundColor: Colors.tealDim, alignItems: 'center', justifyContent: 'center' },
  successTitle: { color: Colors.white, fontSize: 24, fontWeight: '800' },
  successCard: { width: '100%', gap: Spacing.sm },
  successRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  successVal: { color: Colors.white, fontSize: 14, fontWeight: '500' },
});
