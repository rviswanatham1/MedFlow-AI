import React, { useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, Animated,
  TouchableOpacity, Dimensions, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons, Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../constants/theme';
import { Button } from '../components/ui';

const { width, height } = Dimensions.get('window');

export default function SplashScreen() {
  const router = useRouter();
  const fadeIn = useRef(new Animated.Value(0)).current;
  const slideUp = useRef(new Animated.Value(40)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeIn, { toValue: 1, duration: 900, delay: 200, useNativeDriver: true }),
      Animated.spring(slideUp, { toValue: 0, delay: 300, useNativeDriver: true, tension: 60 }),
    ]).start();
  }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={[styles.glowOrb, { top: -80, left: -80 }]} />
        <View style={[styles.glowOrb2, { bottom: 100, right: -60 }]} />

        <Animated.View style={[styles.content, { opacity: fadeIn, transform: [{ translateY: slideUp }] }]}>
          {/* Logo */}
          <View style={styles.logoSection}>
            <View style={styles.logoIconBg}>
              <MaterialCommunityIcons name="heart-pulse" size={32} color={Colors.teal} />
            </View>
            <Text style={styles.logoText}>MedFlow<Text style={styles.logoAI}>AI</Text></Text>
          </View>

          <Text style={styles.tagline}>Intelligent triage.{'\n'}Smarter care.</Text>

          {/* Feature pills */}
          <View style={styles.pills}>
            {[
              { icon: 'brain', label: 'AI Symptom Analysis' },
              { icon: 'clock-fast', label: 'Real-time Wait Times' },
              { icon: 'shield-check', label: 'Smart Escalation' },
            ].map(f => (
              <View key={f.label} style={styles.pill}>
                <MaterialCommunityIcons name={f.icon as any} size={15} color={Colors.teal} />
                <Text style={styles.pillText}>{f.label}</Text>
              </View>
            ))}
          </View>

          <View style={styles.actions}>
            <Button label="I'm a Patient" onPress={() => router.push('/auth/login?role=patient')} size="lg" style={{ width: '100%' }} />
            <Button label="Staff / Clinician" onPress={() => router.push('/auth/login?role=staff')} variant="outline" size="lg" style={{ width: '100%' }} />
          </View>

          <Text style={styles.footer}>HIPAA Compliant · AES-256 Encrypted · SOC 2</Text>
        </Animated.View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Colors.navy },
  container: { flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center', padding: Spacing.lg },
  glowOrb: { position: 'absolute', width: 260, height: 260, borderRadius: 130, backgroundColor: Colors.teal, opacity: 0.07 },
  glowOrb2: { position: 'absolute', width: 200, height: 200, borderRadius: 100, backgroundColor: Colors.blue, opacity: 0.06 },
  content: { width: '100%', alignItems: 'center', gap: Spacing.xl },
  logoSection: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  logoIconBg: {
    width: 52, height: 52, borderRadius: 26,
    backgroundColor: Colors.tealDim, borderWidth: 2, borderColor: `${Colors.teal}44`,
    alignItems: 'center', justifyContent: 'center',
  },
  logoText: { fontSize: 42, fontWeight: '900', color: Colors.white, letterSpacing: -1 },
  logoAI: { color: Colors.teal },
  tagline: { fontSize: 22, color: Colors.gray400, textAlign: 'center', lineHeight: 32, fontWeight: '300' },
  pills: { gap: Spacing.sm, width: '100%' },
  pill: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}22`,
    borderRadius: Radius.full, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
  },
  pillText: { color: Colors.gray400, fontSize: 13, fontWeight: '500' },
  actions: { width: '100%', gap: Spacing.sm },
  footer: { color: Colors.gray600, fontSize: 10, letterSpacing: 0.8, textAlign: 'center' },
});
