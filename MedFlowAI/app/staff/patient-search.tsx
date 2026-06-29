import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, SafeAreaView, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Divider } from '../../components/ui';
import { api } from '../../services/api';

interface PatientResult {
  patient_id: string;
  name: string;
  dob: string;
  gender: string;
  insurance: string;
  last_triage?: string;
}

type SearchField = 'name' | 'mrn';

export default function PatientSearchScreen() {
  const router = useRouter();
  const [query, setQuery]       = useState('');
  const [field, setField]       = useState<SearchField>('name');
  const [results, setResults]   = useState<PatientResult[]>([]);
  const [loading, setLoading]   = useState(false);
  const [searched, setSearched] = useState(false);
  const [selected, setSelected] = useState<PatientResult | null>(null);
  const inputRef = useRef<TextInput>(null);

  const FIELDS: { key: SearchField; label: string; placeholder: string }[] = [
    { key: 'name', label: 'Name', placeholder: 'e.g. Sarah Johnson' },
    { key: 'mrn',  label: 'MRN',  placeholder: 'e.g. PT001' },
  ];

  // Load recent patients on mount (blank query returns up to 20)
  useEffect(() => {
    api.searchPatients('', 'name')
      .then(setResults)
      .catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    setSelected(null);
    try {
      const data = await api.searchPatients(query.trim(), field);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery('');
    setSearched(false);
    setSelected(null);
    api.searchPatients('', 'name').then(setResults).catch(() => {});
  };

  const initials = (name: string) =>
    name.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase();

  const formatDate = (iso: string) => {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
    catch { return iso.slice(0, 10); }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Patient Search</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

        {/* Field selector */}
        <View style={styles.fieldRow}>
          {FIELDS.map(f => (
            <TouchableOpacity
              key={f.key}
              style={[styles.fieldChip, field === f.key && styles.fieldChipActive]}
              onPress={() => { setField(f.key); setQuery(''); inputRef.current?.focus(); }}
            >
              <Text style={[styles.fieldText, field === f.key && styles.fieldTextActive]}>{f.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Search input */}
        <View style={styles.searchRow}>
          <View style={styles.searchBox}>
            <MaterialCommunityIcons name="magnify" size={20} color={Colors.gray400} />
            <TextInput
              ref={inputRef}
              style={styles.searchInput}
              value={query}
              onChangeText={setQuery}
              placeholder={FIELDS.find(f => f.key === field)?.placeholder}
              placeholderTextColor={Colors.gray600}
              autoCapitalize={field === 'mrn' ? 'characters' : 'words'}
              onSubmitEditing={handleSearch}
              returnKeyType="search"
            />
            {query.length > 0 && (
              <TouchableOpacity onPress={handleClear}>
                <MaterialCommunityIcons name="close-circle" size={18} color={Colors.gray400} />
              </TouchableOpacity>
            )}
          </View>
          <TouchableOpacity style={styles.searchBtn} onPress={handleSearch}>
            <Text style={styles.searchBtnText}>Search</Text>
          </TouchableOpacity>
        </View>

        {/* Loading */}
        {loading && (
          <View style={styles.centered}>
            <ActivityIndicator color={Colors.teal} />
          </View>
        )}

        {/* Empty state */}
        {!loading && searched && results.length === 0 && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="account-search-outline" size={48} color={Colors.gray600} />
            <Text style={styles.emptyTitle}>No patients found</Text>
            <Text style={styles.emptyText}>Try a different name or MRN</Text>
          </View>
        )}

        {/* Section label */}
        {!loading && results.length > 0 && (
          <Text style={styles.sectionTitle}>
            {searched ? `${results.length} result${results.length !== 1 ? 's' : ''}` : 'All Patients'}
          </Text>
        )}

        {/* Results */}
        {!loading && results.map(p => {
          const isSelected = selected?.patient_id === p.patient_id;
          return (
            <View key={p.patient_id}>
              <TouchableOpacity onPress={() => setSelected(isSelected ? null : p)}>
                <GlassCard style={[styles.resultCard, isSelected && styles.resultCardActive]}>
                  <View style={styles.resultHeader}>
                    <View style={styles.resultLeft}>
                      <View style={styles.resultAvatar}>
                        <Text style={styles.resultAvatarText}>{initials(p.name)}</Text>
                      </View>
                      <View>
                        <Text style={styles.resultName}>{p.name}</Text>
                        <Text style={styles.resultId}>{p.patient_id}</Text>
                      </View>
                    </View>
                    <MaterialCommunityIcons
                      name={isSelected ? 'chevron-up' : 'chevron-down'}
                      size={16}
                      color={Colors.gray600}
                    />
                  </View>

                  <View style={styles.metaRow}>
                    {!!p.dob && (
                      <View style={styles.metaItem}>
                        <MaterialCommunityIcons name="calendar-outline" size={12} color={Colors.gray600} />
                        <Text style={styles.metaText}>
                          {p.dob}{p.gender ? ` · ${p.gender}` : ''}
                        </Text>
                      </View>
                    )}
                    {!!p.insurance && (
                      <View style={styles.metaItem}>
                        <MaterialCommunityIcons name="shield-check-outline" size={12} color={Colors.gray600} />
                        <Text style={styles.metaText}>{p.insurance}</Text>
                      </View>
                    )}
                    {!!p.last_triage && (
                      <View style={styles.metaItem}>
                        <MaterialCommunityIcons name="clock-outline" size={12} color={Colors.gray600} />
                        <Text style={styles.metaText}>Last triage: {formatDate(p.last_triage)}</Text>
                      </View>
                    )}
                  </View>
                </GlassCard>
              </TouchableOpacity>

              {/* Expanded actions */}
              {isSelected && (
                <GlassCard style={styles.actionPanel}>
                  <View style={styles.actionGrid}>
                    {[
                      { label: 'View Full Record', icon: 'file-document-outline',   color: Colors.teal,  onPress: () => router.push({ pathname: '/staff/patient-detail', params: { id: p.patient_id } }) },
                      { label: 'Add to Queue',     icon: 'playlist-plus',           color: Colors.blue,  onPress: () => {} },
                      { label: 'Start Intake',     icon: 'clipboard-text-outline',  color: Colors.amber, onPress: () => {} },
                      { label: 'Assign Resource',  icon: 'bed-outline',             color: Colors.green, onPress: () => router.push('/staff/resource-allocation') },
                    ].map(a => (
                      <TouchableOpacity key={a.label} style={styles.actionBtn} onPress={a.onPress}>
                        <View style={[styles.actionIconBg, { backgroundColor: `${a.color}18` }]}>
                          <MaterialCommunityIcons name={a.icon as any} size={20} color={a.color} />
                        </View>
                        <Text style={styles.actionBtnText}>{a.label}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </GlassCard>
              )}
            </View>
          );
        })}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header:          { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn:         { width: 40, height: 40, justifyContent: 'center' },
  headerTitle:     { color: Colors.white, fontSize: 17, fontWeight: '700' },
  scroll:          { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  fieldRow:        { flexDirection: 'row', gap: Spacing.xs },
  fieldChip:       { flex: 1, alignItems: 'center', paddingVertical: Spacing.xs + 2, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full },
  fieldChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  fieldText:       { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  fieldTextActive: { color: Colors.teal },
  searchRow:       { flexDirection: 'row', gap: Spacing.sm },
  searchBox:       { flex: 1, flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm },
  searchInput:     { flex: 1, color: Colors.white, fontSize: 15 },
  searchBtn:       { backgroundColor: Colors.teal, borderRadius: Radius.md, paddingHorizontal: Spacing.lg, justifyContent: 'center' },
  searchBtnText:   { color: Colors.navy, fontWeight: '800', fontSize: 14 },
  centered:        { alignItems: 'center', paddingVertical: Spacing.xl },
  emptyState:      { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xxl },
  emptyTitle:      { color: Colors.white, fontSize: 17, fontWeight: '700' },
  emptyText:       { color: Colors.gray400, fontSize: 14 },
  sectionTitle:    { color: Colors.gray400, fontSize: 12, fontWeight: '700', letterSpacing: 0.5 },
  resultCard:      { gap: Spacing.sm },
  resultCardActive:{ borderColor: `${Colors.teal}55`, backgroundColor: Colors.tealDim2 },
  resultHeader:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  resultLeft:      { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  resultAvatar:    { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.navyLight, alignItems: 'center', justifyContent: 'center' },
  resultAvatarText:{ color: Colors.teal, fontWeight: '800', fontSize: 13 },
  resultName:      { color: Colors.white, fontSize: 15, fontWeight: '700' },
  resultId:        { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  metaRow:         { gap: 5 },
  metaItem:        { flexDirection: 'row', alignItems: 'center', gap: 6 },
  metaText:        { color: Colors.gray600, fontSize: 12 },
  actionPanel:     { marginTop: -Spacing.sm, backgroundColor: Colors.navyMid, gap: Spacing.md },
  actionGrid:      { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  actionBtn:       { width: '47%', flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.sm },
  actionIconBg:    { width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center' },
  actionBtnText:   { color: Colors.white, fontSize: 12, fontWeight: '600', flex: 1 },
});
