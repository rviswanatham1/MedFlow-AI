import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  SafeAreaView, ActivityIndicator, TextInput, Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Button } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api, LabOrder, Medication, CarePlan } from '../../services/api';

export default function CarePlanScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { clinicianId } = useApp();

  const [existing, setExisting] = useState<CarePlan | null>(null);
  const [isAiSuggestion, setIsAiSuggestion] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Labs state
  const [labs, setLabs] = useState<LabOrder[]>([
    { name: '', urgency: 'Routine', timing: '', notes: '' },
  ]);

  // Medications state
  const [meds, setMeds] = useState<Medication[]>([
    { name: '', dose: '', frequency: '', route: 'PO', duration: '', notes: '' },
  ]);

  // Other fields
  const [instructions, setInstructions] = useState('');
  const [followUp, setFollowUp] = useState('');
  const [diet, setDiet] = useState('');
  const [activity, setActivity] = useState('');

  useEffect(() => {
    if (!id) return;
    api.getCarePlan(id, 'doctor').then((plan: any) => {
      if (plan.exists) {
        setExisting(plan);
        setIsAiSuggestion(!!plan.is_ai_suggestion);
        setLabs(plan.labs?.length ? plan.labs : [{ name: '', urgency: 'Routine', timing: '', notes: '' }]);
        setMeds(plan.medications?.length ? plan.medications : [{ name: '', dose: '', frequency: '', route: 'PO', duration: '', notes: '' }]);
        setInstructions(plan.instructions ?? '');
        setFollowUp(plan.follow_up ?? '');
        setDiet(plan.diet ?? '');
        setActivity(plan.activity ?? '');
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const addLab = () => setLabs(prev => [...prev, { name: '', urgency: 'Routine', timing: '', notes: '' }]);
  const removeLab = (i: number) => setLabs(prev => prev.filter((_, idx) => idx !== i));
  const updateLab = (i: number, patch: Partial<LabOrder>) =>
    setLabs(prev => prev.map((l, idx) => idx === i ? { ...l, ...patch } : l));

  const addMed = () => setMeds(prev => [...prev, { name: '', dose: '', frequency: '', route: 'PO', duration: '', notes: '' }]);
  const removeMed = (i: number) => setMeds(prev => prev.filter((_, idx) => idx !== i));
  const updateMed = (i: number, patch: Partial<Medication>) =>
    setMeds(prev => prev.map((m, idx) => idx === i ? { ...m, ...patch } : m));

  const handleApprove = async () => {
    if (!id) return;
    const validLabs = labs.filter(l => l.name.trim());
    const validMeds = meds.filter(m => m.name.trim());
    if (!validLabs.length && !validMeds.length && !instructions.trim()) {
      Alert.alert('Care Plan Empty', 'Please add at least one lab, medication, or instruction.');
      return;
    }
    setSaving(true);
    try {
      await api.saveCarePlan({
        patient_id: id,
        doctor_id: clinicianId,
        labs: validLabs,
        medications: validMeds,
        instructions,
        follow_up: followUp,
        diet: diet || undefined,
        activity: activity || undefined,
      });
      Alert.alert(
        'Care Plan Approved ✓',
        'The care plan has been shared with nursing staff for Epic/SIS entry and released to the patient.',
        [{ text: 'Back to Dashboard', onPress: () => router.replace('/staff/dashboard' as any) }]
      );
    } catch (e) {
      Alert.alert('Error', 'Failed to save care plan. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator color={Colors.teal} size="large" />
    </SafeAreaView>
  );

  const urgencyOptions: LabOrder['urgency'][] = ['STAT', 'ASAP', 'Routine'];
  const routeOptions = ['PO', 'IV', 'IM', 'SQ', 'Topical', 'Inhaled'];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <View style={{ alignItems: 'center' }}>
          <Text style={styles.headerTitle}>Create Care Plan</Text>
          <Text style={styles.headerSub}>{id} · Step 2 of 2</Text>
        </View>
        <View style={{ width: 40 }} />
      </View>

      {existing && isAiSuggestion && (
        <View style={[styles.existingBanner, { backgroundColor: `${Colors.amber}12`, borderBottomColor: `${Colors.amber}30` }]}>
          <MaterialCommunityIcons name="robot-outline" size={14} color={Colors.amber} />
          <Text style={[styles.existingText, { color: Colors.amber }]}>AI-suggested care plan — review, edit if needed, then approve to share with staff and patient.</Text>
        </View>
      )}
      {existing && !isAiSuggestion && (
        <View style={styles.existingBanner}>
          <MaterialCommunityIcons name="check-circle" size={14} color={Colors.teal} />
          <Text style={styles.existingText}>Previously approved — editing will re-share with staff and patient.</Text>
        </View>
      )}

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">

        {/* Labs Section */}
        <GlassCard style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <MaterialCommunityIcons name="test-tube" size={16} color={Colors.amber} />
            <Text style={styles.sectionTitle}>Labs & Tests Ordered</Text>
          </View>
          {labs.map((lab, i) => (
            <View key={i} style={styles.itemBlock}>
              <View style={styles.itemBlockHeader}>
                <Text style={styles.itemNum}>Lab {i + 1}</Text>
                {labs.length > 1 && (
                  <TouchableOpacity onPress={() => removeLab(i)}>
                    <MaterialCommunityIcons name="close-circle" size={18} color={Colors.red} />
                  </TouchableOpacity>
                )}
              </View>
              <Text style={styles.fieldLabel}>Test Name</Text>
              <TextInput
                style={styles.input}
                value={lab.name}
                onChangeText={v => updateLab(i, { name: v })}
                placeholder="e.g. CBC, Troponin, BMP..."
                placeholderTextColor={Colors.gray600}
              />
              <View style={{ flexDirection: 'row', gap: Spacing.sm }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>Urgency</Text>
                  <View style={styles.chipRow}>
                    {urgencyOptions.map(u => (
                      <TouchableOpacity
                        key={u}
                        style={[styles.optionChip, lab.urgency === u && styles.optionChipActive,
                          u === 'STAT' && lab.urgency === u && { backgroundColor: `${Colors.red}30`, borderColor: Colors.red }]}
                        onPress={() => updateLab(i, { urgency: u })}
                      >
                        <Text style={[styles.optionChipText, lab.urgency === u && { color: u === 'STAT' ? Colors.red : Colors.teal }]}>{u}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              </View>
              <Text style={styles.fieldLabel}>Timing / Instructions</Text>
              <TextInput
                style={styles.input}
                value={lab.timing}
                onChangeText={v => updateLab(i, { timing: v })}
                placeholder="e.g. Within 30 min, serial q3h..."
                placeholderTextColor={Colors.gray600}
              />
            </View>
          ))}
          <TouchableOpacity style={styles.addBtn} onPress={addLab}>
            <MaterialCommunityIcons name="plus-circle-outline" size={16} color={Colors.amber} />
            <Text style={[styles.addBtnText, { color: Colors.amber }]}>Add Lab</Text>
          </TouchableOpacity>
        </GlassCard>

        {/* Medications Section */}
        <GlassCard style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <MaterialCommunityIcons name="pill" size={16} color={Colors.teal} />
            <Text style={styles.sectionTitle}>Medications</Text>
          </View>
          {meds.map((med, i) => (
            <View key={i} style={styles.itemBlock}>
              <View style={styles.itemBlockHeader}>
                <Text style={styles.itemNum}>Med {i + 1}</Text>
                {meds.length > 1 && (
                  <TouchableOpacity onPress={() => removeMed(i)}>
                    <MaterialCommunityIcons name="close-circle" size={18} color={Colors.red} />
                  </TouchableOpacity>
                )}
              </View>
              <Text style={styles.fieldLabel}>Medication Name</Text>
              <TextInput
                style={styles.input}
                value={med.name}
                onChangeText={v => updateMed(i, { name: v })}
                placeholder="e.g. Aspirin, Metoprolol..."
                placeholderTextColor={Colors.gray600}
              />
              <View style={{ flexDirection: 'row', gap: Spacing.sm }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>Dose</Text>
                  <TextInput
                    style={styles.input}
                    value={med.dose}
                    onChangeText={v => updateMed(i, { dose: v })}
                    placeholder="e.g. 325mg"
                    placeholderTextColor={Colors.gray600}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.fieldLabel}>Frequency</Text>
                  <TextInput
                    style={styles.input}
                    value={med.frequency}
                    onChangeText={v => updateMed(i, { frequency: v })}
                    placeholder="e.g. Once, BID, TID"
                    placeholderTextColor={Colors.gray600}
                  />
                </View>
              </View>
              <Text style={styles.fieldLabel}>Route</Text>
              <View style={styles.chipRow}>
                {routeOptions.map(r => (
                  <TouchableOpacity
                    key={r}
                    style={[styles.optionChip, med.route === r && styles.optionChipActive]}
                    onPress={() => updateMed(i, { route: r })}
                  >
                    <Text style={[styles.optionChipText, med.route === r && { color: Colors.teal }]}>{r}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={styles.fieldLabel}>Duration (optional)</Text>
              <TextInput
                style={styles.input}
                value={med.duration ?? ''}
                onChangeText={v => updateMed(i, { duration: v })}
                placeholder="e.g. 7 days, until discharge"
                placeholderTextColor={Colors.gray600}
              />
              <Text style={styles.fieldLabel}>Notes (optional)</Text>
              <TextInput
                style={styles.input}
                value={med.notes ?? ''}
                onChangeText={v => updateMed(i, { notes: v })}
                placeholder="Special instructions, contraindications..."
                placeholderTextColor={Colors.gray600}
                multiline
              />
            </View>
          ))}
          <TouchableOpacity style={styles.addBtn} onPress={addMed}>
            <MaterialCommunityIcons name="plus-circle-outline" size={16} color={Colors.teal} />
            <Text style={styles.addBtnText}>Add Medication</Text>
          </TouchableOpacity>
        </GlassCard>

        {/* Instructions & Follow-up */}
        <GlassCard style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <MaterialCommunityIcons name="clipboard-text-outline" size={16} color={Colors.blue} />
            <Text style={styles.sectionTitle}>Patient Instructions</Text>
          </View>

          <Text style={styles.fieldLabel}>General Instructions</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            value={instructions}
            onChangeText={setInstructions}
            placeholder="Post-visit care, wound care, activity restrictions..."
            placeholderTextColor={Colors.gray600}
            multiline
            textAlignVertical="top"
          />

          <Text style={styles.fieldLabel}>Follow-Up</Text>
          <TextInput
            style={styles.input}
            value={followUp}
            onChangeText={setFollowUp}
            placeholder="e.g. Return in 48h, follow up with cardiologist in 1 week"
            placeholderTextColor={Colors.gray600}
          />

          <Text style={styles.fieldLabel}>Diet Restrictions (optional)</Text>
          <TextInput
            style={styles.input}
            value={diet}
            onChangeText={setDiet}
            placeholder="e.g. Low sodium, NPO until further notice"
            placeholderTextColor={Colors.gray600}
          />

          <Text style={styles.fieldLabel}>Activity Restrictions (optional)</Text>
          <TextInput
            style={styles.input}
            value={activity}
            onChangeText={setActivity}
            placeholder="e.g. Bed rest 24h, no strenuous activity for 2 weeks"
            placeholderTextColor={Colors.gray600}
          />
        </GlassCard>

        {/* Approve */}
        <GlassCard style={{ gap: Spacing.sm, borderColor: `${Colors.teal}33`, borderWidth: 1 }}>
          <View style={styles.sectionHeader}>
            <MaterialCommunityIcons name="shield-check-outline" size={16} color={Colors.teal} />
            <Text style={styles.sectionTitle}>Approve & Share</Text>
          </View>
          <Text style={{ color: Colors.gray400, fontSize: 13, lineHeight: 20 }}>
            This is Step 2. Approving will share the care plan with nursing staff (for Epic/SIS entry) and release it to the patient. The diagnosis was already shared with staff in Step 1.
          </Text>
          <Button
            label={saving ? 'Approving…' : (existing && !isAiSuggestion ? 'Update & Re-share Plan' : 'Approve & Share Care Plan')}
            onPress={handleApprove}
            loading={saving}
            size="lg"
            style={{ marginTop: Spacing.xs }}
          />
        </GlassCard>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  iconBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  headerSub: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  existingBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.teal}12`, borderBottomWidth: 1, borderBottomColor: `${Colors.teal}30`, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm },
  existingText: { color: Colors.teal, fontSize: 12, flex: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  sectionCard: { gap: Spacing.sm },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.xs },
  sectionTitle: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  itemBlock: { backgroundColor: Colors.navyMid, borderRadius: Radius.md, padding: Spacing.md, gap: Spacing.sm, marginBottom: Spacing.sm, borderWidth: 1, borderColor: Colors.glassBorder },
  itemBlockHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  itemNum: { color: Colors.gray400, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  fieldLabel: { color: Colors.gray400, fontSize: 11, fontWeight: '600', letterSpacing: 0.3, marginBottom: 3 },
  input: { backgroundColor: Colors.navy, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: 8, color: Colors.white, fontSize: 13 },
  textArea: { minHeight: 80, textAlignVertical: 'top' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  optionChip: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: Radius.full, borderWidth: 1, borderColor: Colors.glassBorder, backgroundColor: Colors.navyLight },
  optionChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  optionChipText: { color: Colors.gray400, fontSize: 11, fontWeight: '700' },
  addBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6 },
  addBtnText: { color: Colors.teal, fontSize: 13, fontWeight: '600' },
});
