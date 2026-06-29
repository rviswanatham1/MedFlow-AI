import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  Animated, KeyboardAvoidingView, Platform, ScrollView, SafeAreaView, Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { Button, GlassCard } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import { PatientProfile } from '../../context/AppContext';

export default function LoginScreen() {
  const router = useRouter();
  const { role } = useLocalSearchParams<{ role: string }>();
  const isStaff = role === 'staff';
  const { setPatientId, setRole, setClinicianId, setProfile } = useApp();

  const [patientId, setPatientIdInput] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeField, setActiveField] = useState<string | null>(null);
  const fadeIn = useRef(new Animated.Value(0)).current;
  const slideUp = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeIn, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.spring(slideUp, { toValue: 0, useNativeDriver: true, tension: 60 }),
    ]).start();
  }, []);

  const handleLogin = async () => {
    if (!patientId.trim() || !password.trim()) {
      Alert.alert('Missing Fields', 'Please enter your Patient ID and password.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.login(patientId.trim(), password, isStaff ? 'staff' : 'patient');
      if (res.success) {
        if (isStaff) {
          setRole('clinician');
          setClinicianId(res.patient_id);
        } else {
          setRole('patient');
          setPatientId(res.patient_id);
          // fetch and cache patient profile
          api.getPatientProfile(res.patient_id)
            .then(setProfile)
            .catch(() => {});
        }
        router.replace(isStaff ? '/staff/dashboard' : '/patient/home');
      }
    } catch (err: any) {
      const msg = err?.message?.includes('401')
        ? isStaff ? 'Invalid Staff ID or password.' : 'Patient ID or password is incorrect.'
        : 'Could not connect to server. Please try again.';
      Alert.alert('Login Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <TouchableOpacity style={styles.back} onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={20} color={Colors.gray400} />
            <Text style={styles.backText}>Back</Text>
          </TouchableOpacity>

          <Animated.View style={[styles.content, { opacity: fadeIn, transform: [{ translateY: slideUp }] }]}>
            <View style={styles.header}>
              <View style={[styles.roleChip, { backgroundColor: isStaff ? `${Colors.blue}22` : Colors.tealDim }]}>
                <MaterialCommunityIcons
                  name={isStaff ? 'stethoscope' : 'account'}
                  size={13}
                  color={isStaff ? Colors.blue : Colors.teal}
                />
                <Text style={[styles.roleChipText, { color: isStaff ? Colors.blue : Colors.teal }]}>
                  {isStaff ? 'Staff / Clinician' : 'Patient'}
                </Text>
              </View>
              <Text style={styles.title}>Welcome back</Text>
            </View>

            <GlassCard style={styles.form}>
              <View style={styles.fieldGroup}>
                <Text style={styles.fieldLabel}>{isStaff ? 'Staff ID' : 'Patient ID'}</Text>
                <View style={[styles.inputWrapper, activeField === 'pid' && styles.inputActive]}>
                  <Ionicons name="card-outline" size={18} color={Colors.gray400} />
                  <TextInput
                    style={styles.input}
                    value={patientId}
                    onChangeText={setPatientIdInput}
                    placeholder={isStaff ? 'e.g. STAFF001' : 'e.g. P00001'}
                    placeholderTextColor={Colors.gray600}
                    autoCapitalize="characters"
                    autoCorrect={false}
                    onFocus={() => setActiveField('pid')}
                    onBlur={() => setActiveField(null)}
                  />
                </View>
              </View>

              <View style={styles.fieldGroup}>
                <Text style={styles.fieldLabel}>Password</Text>
                <View style={[styles.inputWrapper, activeField === 'password' && styles.inputActive]}>
                  <Ionicons name="lock-closed-outline" size={18} color={Colors.gray400} />
                  <TextInput
                    style={styles.input}
                    value={password}
                    onChangeText={setPassword}
                    placeholder="••••••••"
                    placeholderTextColor={Colors.gray600}
                    secureTextEntry={!showPassword}
                    onFocus={() => setActiveField('password')}
                    onBlur={() => setActiveField(null)}
                  />
                  <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                    <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={18} color={Colors.gray400} />
                  </TouchableOpacity>
                </View>
              </View>

              <TouchableOpacity style={styles.forgotRow}>
                <Text style={styles.forgotText}>Forgot password?</Text>
              </TouchableOpacity>

              <Button label="Sign In" onPress={handleLogin} loading={loading} size="lg" style={{ marginTop: Spacing.xs }} />
            </GlassCard>

            <View style={styles.biometricRow}>
              <View style={styles.biometricDivider} />
              <Text style={styles.biometricLabel}>or</Text>
              <View style={styles.biometricDivider} />
            </View>

            <TouchableOpacity style={styles.biometricBtn}>
              <MaterialCommunityIcons name="fingerprint" size={26} color={Colors.teal} />
              <Text style={styles.biometricBtnText}>Use Biometrics</Text>
            </TouchableOpacity>

            {!isStaff && (
              <TouchableOpacity style={styles.registerRow} onPress={() => router.push('/auth/register')}>
                <Text style={styles.registerText}>New patient? </Text>
                <Text style={styles.registerLink}>Create account →</Text>
              </TouchableOpacity>
            )}
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: Colors.navy, padding: Spacing.lg },
  back: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: Spacing.md, marginBottom: Spacing.xl },
  backText: { color: Colors.gray400, fontSize: 14 },
  content: { gap: Spacing.lg },
  header: { gap: Spacing.sm },
  roleChip: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', borderRadius: Radius.full, paddingHorizontal: 12, paddingVertical: 5 },
  roleChipText: { fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  title: { color: Colors.white, fontSize: 32, fontWeight: '800', letterSpacing: -0.5 },
  form: { gap: Spacing.md },
  fieldGroup: { gap: Spacing.xs + 2 },
  fieldLabel: { color: Colors.gray400, fontSize: 12, fontWeight: '600', letterSpacing: 0.5 },
  inputWrapper: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder,
    borderRadius: Radius.md, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm + 2,
  },
  inputActive: { borderColor: Colors.teal, shadowColor: Colors.teal, shadowOffset: { width: 0, height: 0 }, shadowOpacity: 0.2, shadowRadius: 8 },
  input: { flex: 1, color: Colors.white, fontSize: 15 },
  forgotRow: { alignItems: 'flex-end' },
  forgotText: { color: Colors.teal, fontSize: 13, fontWeight: '500' },
  biometricRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  biometricDivider: { flex: 1, height: 1, backgroundColor: Colors.glassBorder },
  biometricLabel: { color: Colors.gray600, fontSize: 13 },
  biometricBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm,
    backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}30`,
    borderRadius: Radius.md, padding: Spacing.md,
  },
  biometricBtnText: { color: Colors.teal, fontSize: 15, fontWeight: '600' },
  registerRow: { flexDirection: 'row', justifyContent: 'center' },
  registerText: { color: Colors.gray400, fontSize: 14 },
  registerLink: { color: Colors.teal, fontSize: 14, fontWeight: '600' },
});
