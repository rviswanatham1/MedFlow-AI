import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, KeyboardAvoidingView, Platform, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { Button, GlassCard } from '../../components/ui';

const STEPS = ['Personal', 'Contact', 'Insurance'];

export default function RegisterScreen() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({ firstName:'', lastName:'', dob:'', sex:'', phone:'', email:'', emergencyContact:'', emergencyPhone:'', insuranceProvider:'', memberId:'', groupNumber:'' });
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const u = (key: string, val: string) => setForm(f => ({ ...f, [key]: val }));

  const Field = ({ label, field, placeholder, keyboardType='default', autoCapitalize='words' }: any) => (
    <View style={styles.fieldGroup}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput style={styles.input} value={form[field as keyof typeof form]} onChangeText={v => u(field, v)} placeholder={placeholder} placeholderTextColor={Colors.gray600} keyboardType={keyboardType} autoCapitalize={autoCapitalize} />
    </View>
  );

  const handleNext = () => {
    if (step < 2) { setStep(s => s + 1); return; }
    setLoading(true);
    // TODO: POST /api/auth/register
    setTimeout(() => { setLoading(false); setDone(true); }, 1200);
  };

  if (done) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
        <View style={styles.successContainer}>
          <MaterialCommunityIcons name="check-circle" size={72} color={Colors.teal} />
          <Text style={styles.successTitle}>You're all set!</Text>
          <Text style={styles.successText}>Your patient account has been created.</Text>
          <Button label="Go to Dashboard" onPress={() => router.replace('/patient/home')} size="lg" style={{ width: '100%' }} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <TouchableOpacity style={styles.back} onPress={() => step > 0 ? setStep(s => s - 1) : router.back()}>
            <Ionicons name="arrow-back" size={20} color={Colors.gray400} />
            <Text style={styles.backText}>{step > 0 ? 'Previous' : 'Back'}</Text>
          </TouchableOpacity>

          <Text style={styles.title}>Create Account</Text>

          {/* Steps */}
          <View style={styles.steps}>
            {STEPS.map((s, i) => (
              <View key={s} style={styles.stepItem}>
                <View style={[styles.stepDot, i <= step && styles.stepDotActive, i < step && styles.stepDotDone]}>
                  {i < step
                    ? <MaterialCommunityIcons name="check" size={13} color={Colors.navy} />
                    : <Text style={[styles.stepNum, i <= step && styles.stepNumActive]}>{i + 1}</Text>
                  }
                </View>
                {i < STEPS.length - 1 && <View style={[styles.stepLine, i < step && styles.stepLineDone]} />}
              </View>
            ))}
          </View>
          <Text style={styles.stepLabel}>{STEPS[step]}</Text>

          {step === 0 && (
            <GlassCard style={styles.form}>
              <Field label="First Name" field="firstName" placeholder="Jane" />
              <Field label="Last Name" field="lastName" placeholder="Doe" />
              <Field label="Date of Birth" field="dob" placeholder="MM/DD/YYYY" keyboardType="numbers-and-punctuation" autoCapitalize="none" />
              <View style={styles.fieldGroup}>
                <Text style={styles.fieldLabel}>Sex</Text>
                <View style={styles.sexRow}>
                  {['Male', 'Female', 'Other'].map(opt => (
                    <TouchableOpacity key={opt} style={[styles.sexChip, form.sex === opt && styles.sexChipActive]} onPress={() => u('sex', opt)}>
                      <Text style={[styles.sexChipText, form.sex === opt && styles.sexChipTextActive]}>{opt}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            </GlassCard>
          )}

          {step === 1 && (
            <GlassCard style={styles.form}>
              <Field label="Phone Number" field="phone" placeholder="+1 (555) 000-0000" keyboardType="phone-pad" autoCapitalize="none" />
              <Field label="Email" field="email" placeholder="jane@email.com" keyboardType="email-address" autoCapitalize="none" />
              <Field label="Emergency Contact" field="emergencyContact" placeholder="John Doe" />
              <Field label="Emergency Phone" field="emergencyPhone" placeholder="+1 (555) 000-0000" keyboardType="phone-pad" autoCapitalize="none" />
            </GlassCard>
          )}

          {step === 2 && (
            <GlassCard style={styles.form}>
              <View style={styles.optionalNote}>
                <MaterialCommunityIcons name="information-outline" size={15} color={Colors.teal} />
                <Text style={styles.optionalText}>Optional — you can add this later in settings.</Text>
              </View>
              <Field label="Insurance Provider" field="insuranceProvider" placeholder="e.g. Blue Cross Blue Shield" />
              <Field label="Member ID" field="memberId" placeholder="Member ID" autoCapitalize="characters" />
              <Field label="Group Number" field="groupNumber" placeholder="Group #" autoCapitalize="none" />
            </GlassCard>
          )}

          <Button label={step === 2 ? 'Create Account' : 'Continue'} onPress={handleNext} loading={loading} size="lg" style={{ marginTop: Spacing.sm }} />
          {step === 2 && (
            <TouchableOpacity style={styles.skipRow} onPress={handleNext}>
              <Text style={styles.skipText}>Skip insurance for now</Text>
            </TouchableOpacity>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: Colors.navy, padding: Spacing.lg, gap: Spacing.md },
  back: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: Spacing.md },
  backText: { color: Colors.gray400, fontSize: 14 },
  title: { color: Colors.white, fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  steps: { flexDirection: 'row', alignItems: 'center' },
  stepItem: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  stepDot: { width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.navyLight, borderWidth: 2, borderColor: Colors.glassBorder, alignItems: 'center', justifyContent: 'center' },
  stepDotActive: { borderColor: Colors.teal },
  stepDotDone: { backgroundColor: Colors.teal, borderColor: Colors.teal },
  stepNum: { color: Colors.gray600, fontSize: 12, fontWeight: '700' },
  stepNumActive: { color: Colors.teal },
  stepLine: { flex: 1, height: 2, backgroundColor: Colors.glassBorder, marginHorizontal: 4 },
  stepLineDone: { backgroundColor: Colors.teal },
  stepLabel: { color: Colors.gray400, fontSize: 13, fontWeight: '600', letterSpacing: 0.5 },
  form: { gap: Spacing.md },
  fieldGroup: { gap: Spacing.xs },
  fieldLabel: { color: Colors.gray400, fontSize: 12, fontWeight: '600', letterSpacing: 0.5 },
  input: { backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm + 2, color: Colors.white, fontSize: 15 },
  sexRow: { flexDirection: 'row', gap: Spacing.sm },
  sexChip: { flex: 1, paddingVertical: Spacing.sm, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, alignItems: 'center' },
  sexChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  sexChipText: { color: Colors.gray400, fontWeight: '600', fontSize: 14 },
  sexChipTextActive: { color: Colors.teal },
  optionalNote: { flexDirection: 'row', gap: Spacing.sm, backgroundColor: Colors.tealDim2, borderRadius: Radius.sm, padding: Spacing.sm, alignItems: 'center' },
  optionalText: { color: Colors.gray400, fontSize: 12, flex: 1 },
  skipRow: { alignItems: 'center', paddingVertical: Spacing.xs },
  skipText: { color: Colors.gray600, fontSize: 13 },
  successContainer: { flex: 1, padding: Spacing.xl, alignItems: 'center', justifyContent: 'center', gap: Spacing.lg },
  successTitle: { color: Colors.white, fontSize: 28, fontWeight: '800' },
  successText: { color: Colors.gray400, textAlign: 'center', fontSize: 15 },
});
