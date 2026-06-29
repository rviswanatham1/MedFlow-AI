import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, Animated, SafeAreaView, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { Button, GlassCard } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import { LLM_PROVIDER, ANTHROPIC_API_KEY, GEMINI_API_KEY } from '../../constants/config';

type InputMode = 'text' | 'voice' | 'image';

const SYMPTOM_SUGGESTIONS = [
  'Chest pain','Difficulty breathing','Severe headache',
  'High fever','Nausea','Dizziness','Back pain',
  'Abdominal pain','Skin rash','Joint pain',
];

export default function SymptomInputScreen() {
  const router = useRouter();
  const { patientId, setTriageResult } = useApp();
  const [mode, setMode] = useState<InputMode>('text');
  const [symptoms, setSymptoms] = useState('');
  const [duration, setDuration] = useState('');
  const [painLevel, setPainLevel] = useState<number | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [imageAttached, setImageAttached] = useState(false);
  const [loading, setLoading] = useState(false);

  // pulse animation for recording state
  const pulse = useRef(new Animated.Value(1)).current;
  const pulseAnim = useRef<Animated.CompositeAnimation | null>(null);

  useEffect(() => {
    if (isRecording) {
      pulseAnim.current = Animated.loop(
        Animated.sequence([
          Animated.timing(pulse, { toValue: 1.18, duration: 700, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1,    duration: 700, useNativeDriver: true }),
        ])
      );
      pulseAnim.current.start();
    } else {
      pulseAnim.current?.stop();
      pulse.setValue(1);
    }
    return () => pulseAnim.current?.stop();
  }, [isRecording]);

  const toggleSuggestion = (s: string) =>
    setSelected(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const result = await api.assessTriage({
        patient_id: patientId,
        symptoms: [symptoms, ...selected].filter(Boolean).join('. '),
        duration: duration || undefined,
        pain_level: painLevel ?? undefined,
        tags: selected,
        provider: LLM_PROVIDER,
        api_key: LLM_PROVIDER === 'anthropic' ? ANTHROPIC_API_KEY
               : LLM_PROVIDER === 'gemini'    ? GEMINI_API_KEY
               : undefined,
      });
      setTriageResult(result);
      router.push('/patient/triage-result');
    } catch (err) {
      Alert.alert('Connection Error', 'Could not reach the AI triage server. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const isReady = symptoms.length > 5 || selected.length > 0;

  const MODES: { key: InputMode; icon: string; label: string }[] = [
    { key: 'text',  icon: 'pencil-outline',    label: 'Text'  },
    { key: 'voice', icon: 'microphone-outline', label: 'Voice' },
    { key: 'image', icon: 'camera-outline',     label: 'Image' },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Symptom Check-In</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Mode switcher */}
        <View style={styles.modeSwitcher}>
          {MODES.map(m => (
            <TouchableOpacity
              key={m.key}
              style={[styles.modeTab, mode === m.key && styles.modeTabActive]}
              onPress={() => setMode(m.key)}
            >
              <MaterialCommunityIcons
                name={m.icon as any}
                size={16}
                color={mode === m.key ? Colors.navy : Colors.gray400}
              />
              <Text style={[styles.modeTabText, mode === m.key && styles.modeTabTextActive]}>
                {m.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── TEXT MODE ── */}
        {mode === 'text' && (
          <GlassCard style={styles.inputCard}>
            <Text style={styles.inputLabel}>Describe your symptoms</Text>
            <TextInput
              style={styles.textArea}
              value={symptoms}
              onChangeText={setSymptoms}
              placeholder="e.g. sharp chest pain on left side, started 2 hours ago..."
              placeholderTextColor={Colors.gray600}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
            />
          </GlassCard>
        )}

        {/* ── VOICE MODE ── */}
        {mode === 'voice' && (
          <GlassCard style={styles.voiceCard} glow={isRecording}>
            <View style={styles.voiceCenter}>
              {/* single animated orb — NO duplicate static orb above */}
              <Animated.View style={[styles.voiceOrbOuter, { transform: [{ scale: pulse }] },
                isRecording && styles.voiceOrbOuterActive]}>
                <TouchableOpacity
                  style={[styles.voiceOrbInner, isRecording && styles.voiceOrbInnerActive]}
                  onPress={() => {
                    setIsRecording(!isRecording);
                    // TODO: ws://api/voice/stream  Speech-to-Text
                    if (isRecording) {
                      setSymptoms(prev => prev + (prev ? ' ' : '') + '[Voice transcription]');
                    }
                  }}
                >
                  <MaterialCommunityIcons
                    name={isRecording ? 'stop' : 'microphone'}
                    size={38}
                    color={isRecording ? Colors.white : Colors.teal}
                  />
                </TouchableOpacity>
              </Animated.View>

              <Text style={[styles.voiceStatus, isRecording && { color: Colors.red }]}>
                {isRecording ? 'Listening...' : 'Tap to speak'}
              </Text>
            </View>

            {symptoms.length > 0 && (
              <View style={styles.transcriptBox}>
                <Text style={styles.transcriptLabel}>Transcribed</Text>
                <Text style={styles.transcriptText}>{symptoms}</Text>
              </View>
            )}
          </GlassCard>
        )}

        {/* ── IMAGE MODE ── */}
        {mode === 'image' && (
          <GlassCard style={styles.inputCard}>
            <Text style={styles.inputLabel}>Upload injury image</Text>
            <TouchableOpacity
              style={styles.imagePicker}
              onPress={() => {
                // TODO: expo-image-picker → POST /api/vision/analyze { image_base64 }
                setImageAttached(true);
              }}
            >
              {imageAttached ? (
                <View style={styles.imageAttached}>
                  <MaterialCommunityIcons name="check-circle" size={32} color={Colors.green} />
                  <Text style={styles.imageAttachedText}>Image attached</Text>
                </View>
              ) : (
                <View style={styles.imagePickerEmpty}>
                  <MaterialCommunityIcons name="camera-plus-outline" size={40} color={Colors.gray400} />
                  <Text style={styles.imagePickerText}>Camera or Gallery</Text>
                </View>
              )}
            </TouchableOpacity>
            <TextInput
              style={[styles.textArea, { marginTop: Spacing.sm, minHeight: 70 }]}
              value={symptoms}
              onChangeText={setSymptoms}
              placeholder="Add description (optional)..."
              placeholderTextColor={Colors.gray600}
              multiline
              textAlignVertical="top"
            />
          </GlassCard>
        )}

        {/* Common symptoms chips */}
        <View>
          <Text style={styles.chipGroupLabel}>Common symptoms</Text>
          <View style={styles.chipsWrap}>
            {SYMPTOM_SUGGESTIONS.map(s => (
              <TouchableOpacity
                key={s}
                style={[styles.chip, selected.includes(s) && styles.chipActive]}
                onPress={() => toggleSuggestion(s)}
              >
                <Text style={[styles.chipText, selected.includes(s) && styles.chipTextActive]}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Duration */}
        <GlassCard>
          <Text style={styles.inputLabel}>Duration</Text>
          <View style={styles.durationRow}>
            {['< 1 hour', '1–6 hrs', '6–24 hrs', '1–3 days', '3+ days'].map(d => (
              <TouchableOpacity
                key={d}
                style={[styles.durationChip, duration === d && styles.durationChipActive]}
                onPress={() => setDuration(d)}
              >
                <Text style={[styles.durationText, duration === d && styles.durationTextActive]}>{d}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </GlassCard>

        {/* Pain level */}
        <GlassCard>
          <Text style={styles.inputLabel}>Pain level</Text>
          <View style={styles.painRow}>
            {[1,2,3,4,5,6,7,8,9,10].map(p => (
              <TouchableOpacity
                key={p}
                style={[
                  styles.painBtn,
                  painLevel === p && styles.painBtnActive,
                  painLevel === p && p >= 7 && { backgroundColor: Colors.red  },
                  painLevel === p && p >= 4 && p < 7 && { backgroundColor: Colors.amber },
                ]}
                onPress={() => setPainLevel(p)}
              >
                <Text style={[styles.painText, painLevel === p && styles.painTextActive]}>{p}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <View style={styles.painLabels}>
            <Text style={styles.painLabelText}>Mild</Text>
            <Text style={styles.painLabelText}>Moderate</Text>
            <Text style={styles.painLabelText}>Severe</Text>
          </View>
        </GlassCard>

        <Button
          label="Analyze & Triage"
          onPress={handleSubmit}
          loading={loading}
          disabled={!isReady}
          size="lg"
          style={{ width: '100%' }}
        />
        <Text style={styles.disclaimer}>
          AI analysis supports triage only. A clinician reviews all recommendations before action.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md,
    borderBottomWidth: 1, borderBottomColor: Colors.glassBorder,
  },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  modeSwitcher: {
    flexDirection: 'row', backgroundColor: Colors.navyMid,
    borderRadius: Radius.md, padding: 4, gap: 4,
  },
  modeTab: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: Spacing.sm, borderRadius: Radius.sm,
  },
  modeTabActive: { backgroundColor: Colors.teal },
  modeTabText: { color: Colors.gray400, fontSize: 13, fontWeight: '600' },
  modeTabTextActive: { color: Colors.navy },
  inputCard: { gap: Spacing.sm },
  inputLabel: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  textArea: {
    color: Colors.white, fontSize: 14, lineHeight: 22, minHeight: 110,
    backgroundColor: Colors.navyMid, borderRadius: Radius.sm,
    padding: Spacing.sm, borderWidth: 1, borderColor: Colors.glassBorder,
  },
  // Voice
  voiceCard: { alignItems: 'center', paddingVertical: Spacing.xl, gap: Spacing.lg },
  voiceCenter: { alignItems: 'center', gap: Spacing.lg },
  voiceOrbOuter: {
    width: 110, height: 110, borderRadius: 55,
    backgroundColor: Colors.tealDim,
    borderWidth: 2, borderColor: `${Colors.teal}55`,
    alignItems: 'center', justifyContent: 'center',
  },
  voiceOrbOuterActive: {
    backgroundColor: `${Colors.red}18`,
    borderColor: `${Colors.red}55`,
  },
  voiceOrbInner: {
    width: 86, height: 86, borderRadius: 43,
    backgroundColor: Colors.navyMid,
    alignItems: 'center', justifyContent: 'center',
  },
  voiceOrbInnerActive: { backgroundColor: `${Colors.red}22` },
  voiceStatus: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  transcriptBox: {
    backgroundColor: Colors.navyMid, borderRadius: Radius.sm,
    padding: Spacing.sm, width: '100%', gap: 4,
    borderWidth: 1, borderColor: Colors.glassBorder,
  },
  transcriptLabel: { color: Colors.gray400, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  transcriptText: { color: Colors.white, fontSize: 14, lineHeight: 20 },
  // Image
  imagePicker: {
    borderWidth: 2, borderStyle: 'dashed', borderColor: Colors.glassBorder,
    borderRadius: Radius.md, padding: Spacing.xl, alignItems: 'center',
  },
  imagePickerEmpty: { alignItems: 'center', gap: Spacing.sm },
  imagePickerText: { color: Colors.gray400, fontSize: 14, fontWeight: '600' },
  imageAttached: { alignItems: 'center', gap: Spacing.xs },
  imageAttachedText: { color: Colors.green, fontSize: 14, fontWeight: '700' },
  // Chips
  chipGroupLabel: {
    color: Colors.gray400, fontSize: 12, fontWeight: '600',
    letterSpacing: 0.5, marginBottom: Spacing.sm,
  },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  chip: {
    paddingHorizontal: Spacing.sm + 4, paddingVertical: Spacing.xs + 2,
    backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder,
    borderRadius: Radius.full,
  },
  chipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  chipText: { color: Colors.gray400, fontSize: 13 },
  chipTextActive: { color: Colors.teal },
  // Duration
  durationRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs, marginTop: Spacing.sm },
  durationChip: {
    paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs + 2,
    backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder,
    borderRadius: Radius.sm,
  },
  durationChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  durationText: { color: Colors.gray400, fontSize: 12 },
  durationTextActive: { color: Colors.teal, fontWeight: '600' },
  // Pain
  painRow: { flexDirection: 'row', gap: 4, marginTop: Spacing.sm },
  painBtn: {
    flex: 1, aspectRatio: 1, borderRadius: Radius.sm,
    backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder,
    alignItems: 'center', justifyContent: 'center',
  },
  painBtnActive: { backgroundColor: Colors.teal, borderColor: Colors.teal },
  painText: { color: Colors.gray400, fontSize: 11, fontWeight: '700' },
  painTextActive: { color: Colors.navy },
  painLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  painLabelText: { color: Colors.gray600, fontSize: 10 },
  disclaimer: { color: Colors.gray600, fontSize: 11, textAlign: 'center', lineHeight: 16 },
});
