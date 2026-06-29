import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Divider } from '../../components/ui';

// Backend connection points for this screen:
// TODO: GET /api/integrations/status       → health check all connected systems
// TODO: GET /api/fhir/sync-status          → last FHIR sync timestamp + record count
// TODO: POST /api/integrations/test/:id    → trigger connectivity test
// TODO: GET /api/hl7/message-log           → recent HL7 message activity

type Status = 'connected' | 'partial' | 'error' | 'pending';

interface Integration {
  id: string;
  name: string;
  category: string;
  description: string;
  status: Status;
  lastSync?: string;
  standard: string;
  icon: string;
  color: string;
  details: string[];
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'epic',
    name: 'Epic MyChart',
    category: 'EHR / EMR',
    description: 'Primary EHR — patient records, scheduling, lab results',
    status: 'connected',
    lastSync: '2 min ago',
    standard: 'FHIR R4 / SMART on FHIR',
    icon: 'hospital-box-outline',
    color: Colors.green,
    details: ['Patient demographics', 'Encounter history', 'Lab results', 'Medications', 'Allergies', 'Immunizations'],
  },
  {
    id: 'cerner',
    name: 'Cerner PowerChart',
    category: 'EHR / EMR',
    description: 'Secondary EHR for outpatient clinic records',
    status: 'partial',
    lastSync: '1h ago',
    standard: 'FHIR R4 / HL7 v2.5',
    icon: 'hospital-building',
    color: Colors.amber,
    details: ['Outpatient encounters', 'Referrals'],
  },
  {
    id: 'bcbs',
    name: 'Blue Cross Blue Shield',
    category: 'Payer / Insurance',
    description: 'Real-time eligibility, prior auth, claims',
    status: 'connected',
    lastSync: '5 min ago',
    standard: 'X12 EDI 270/271/278',
    icon: 'shield-check',
    color: Colors.green,
    details: ['Eligibility verification (270/271)', 'Prior auth (278)', 'Claims submission (837)', 'Remittance (835)'],
  },
  {
    id: 'availity',
    name: 'Availity',
    category: 'Clearinghouse',
    description: 'Multi-payer eligibility and claims clearinghouse',
    status: 'connected',
    lastSync: '10 min ago',
    standard: 'X12 EDI / REST API',
    icon: 'swap-horizontal',
    color: Colors.blue,
    details: ['Real-time eligibility', 'Prior auth routing', 'Claim status', 'ERA / EOB'],
  },
  {
    id: 'lab',
    name: 'Quest Diagnostics',
    category: 'Lab',
    description: 'Lab order routing and result delivery',
    status: 'connected',
    lastSync: '15 min ago',
    standard: 'HL7 v2.5.1 / FHIR R4',
    icon: 'flask-outline',
    color: Colors.teal,
    details: ['Lab orders (ORM)', 'Results (ORU)', 'DiagnosticReport FHIR'],
  },
  {
    id: 'pharmacy',
    name: 'Surescripts',
    category: 'Pharmacy / e-Rx',
    description: 'Electronic prescription routing to pharmacies',
    status: 'connected',
    lastSync: '30 min ago',
    standard: 'NCPDP SCRIPT',
    icon: 'pill',
    color: Colors.teal,
    details: ['NewRx', 'RefillRequest', 'MedicationHistory', 'DrugInteractionCheck'],
  },
  {
    id: 'radiology',
    name: 'PACS / Radiology',
    category: 'Imaging',
    description: 'DICOM image retrieval and radiology reports',
    status: 'partial',
    lastSync: '2h ago',
    standard: 'DICOM / HL7 FHIR ImagingStudy',
    icon: 'radiology-box-outline',
    color: Colors.amber,
    details: ['ImagingStudy FHIR', 'DICOM viewer link-out'],
  },
  {
    id: 'cms',
    name: 'CMS Price Transparency',
    category: 'Price Transparency',
    description: 'Hospital chargemaster and negotiated rate data',
    status: 'connected',
    lastSync: '24h ago',
    standard: 'CMS MRF / JSON',
    icon: 'currency-usd',
    color: Colors.green,
    details: ['Machine-readable files', 'Negotiated rates', 'Standard charges', 'Shoppable services'],
  },
  {
    id: 'audit',
    name: 'Audit & Compliance Log',
    category: 'Compliance',
    description: 'HIPAA audit trail, SOC 2 event log, AI decision log',
    status: 'connected',
    lastSync: 'Live',
    standard: 'Internal / SIEM',
    icon: 'shield-lock-outline',
    color: Colors.teal,
    details: ['All AI outputs logged', 'Clinician approvals', 'PHI access events', 'Role-based access log'],
  },
];

const STATUS_CFG: Record<Status, { label: string; color: string; icon: string }> = {
  connected: { label: 'Connected', color: Colors.green, icon: 'check-circle'       },
  partial:   { label: 'Partial',   color: Colors.amber, icon: 'alert-circle'       },
  error:     { label: 'Error',     color: Colors.red,   icon: 'close-circle'       },
  pending:   { label: 'Pending',   color: Colors.gray400,icon: 'clock-outline'     },
};

const CATEGORIES = ['All', 'EHR / EMR', 'Payer / Insurance', 'Clearinghouse', 'Lab', 'Pharmacy / e-Rx', 'Imaging', 'Price Transparency', 'Compliance'];

export default function IntegrationsScreen() {
  const router = useRouter();
  const [selectedCat, setSelectedCat] = useState('All');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const displayed = selectedCat === 'All'
    ? INTEGRATIONS
    : INTEGRATIONS.filter(i => i.category === selectedCat);

  const connected = INTEGRATIONS.filter(i => i.status === 'connected').length;
  const partial   = INTEGRATIONS.filter(i => i.status === 'partial').length;
  const errors    = INTEGRATIONS.filter(i => i.status === 'error').length;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>System Integrations</Text>
        <View style={styles.fhirBadge}>
          <MaterialCommunityIcons name="link-variant" size={12} color={Colors.teal} />
          <Text style={styles.fhirText}>FHIR R4</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* Status summary */}
        <GlassCard style={styles.summaryCard} glow>
          <Text style={styles.summaryTitle}>Integration Health</Text>
          <View style={styles.summaryRow}>
            <View style={styles.summaryStat}>
              <Text style={[styles.summaryVal, { color: Colors.green }]}>{connected}</Text>
              <Text style={styles.summaryLabel}>Connected</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryStat}>
              <Text style={[styles.summaryVal, { color: Colors.amber }]}>{partial}</Text>
              <Text style={styles.summaryLabel}>Partial</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryStat}>
              <Text style={[styles.summaryVal, { color: errors > 0 ? Colors.red : Colors.gray400 }]}>{errors}</Text>
              <Text style={styles.summaryLabel}>Errors</Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryStat}>
              <Text style={[styles.summaryVal, { color: Colors.teal }]}>{INTEGRATIONS.length}</Text>
              <Text style={styles.summaryLabel}>Total</Text>
            </View>
          </View>
          <View style={styles.fhirNote}>
            <MaterialCommunityIcons name="information-outline" size={13} color={Colors.teal} />
            <Text style={styles.fhirNoteText}>
              All EHR connections use SMART on FHIR OAuth 2.0. PHI encrypted in transit (TLS 1.3) and at rest (AES-256).
            </Text>
          </View>
        </GlassCard>

        {/* Category filter */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.catScroll}>
          {CATEGORIES.map(cat => (
            <TouchableOpacity
              key={cat}
              style={[styles.catChip, selectedCat === cat && styles.catChipActive]}
              onPress={() => setSelectedCat(cat)}
            >
              <Text style={[styles.catText, selectedCat === cat && styles.catTextActive]}>{cat}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Integration cards */}
        {displayed.map(intg => {
          const st = STATUS_CFG[intg.status];
          const isOpen = expandedId === intg.id;
          return (
            <GlassCard key={intg.id} style={[styles.intgCard, intg.status === 'error' && styles.intgCardError]}>
              <TouchableOpacity
                style={styles.intgHeader}
                onPress={() => setExpandedId(isOpen ? null : intg.id)}
              >
                <View style={[styles.intgIconBg, { backgroundColor: `${intg.color}18` }]}>
                  <MaterialCommunityIcons name={intg.icon as any} size={20} color={intg.color} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.intgName}>{intg.name}</Text>
                  <Text style={styles.intgCategory}>{intg.category}</Text>
                </View>
                <View style={styles.intgRight}>
                  <View style={[styles.statusDot, { backgroundColor: st.color }]} />
                  <MaterialCommunityIcons
                    name={isOpen ? 'chevron-up' : 'chevron-down'}
                    size={16}
                    color={Colors.gray400}
                  />
                </View>
              </TouchableOpacity>

              {isOpen && (
                <View style={styles.intgDetails}>
                  <Divider />
                  <Text style={styles.intgDesc}>{intg.description}</Text>

                  <View style={styles.metaRow}>
                    <View style={styles.metaItem}>
                      <Text style={styles.metaLabel}>Standard</Text>
                      <Text style={styles.metaVal}>{intg.standard}</Text>
                    </View>
                    <View style={styles.metaItem}>
                      <Text style={styles.metaLabel}>Last Sync</Text>
                      <Text style={[styles.metaVal, { color: intg.status === 'connected' ? Colors.green : Colors.amber }]}>
                        {intg.lastSync ?? '—'}
                      </Text>
                    </View>
                    <View style={styles.metaItem}>
                      <Text style={styles.metaLabel}>Status</Text>
                      <Text style={[styles.metaVal, { color: st.color }]}>{st.label}</Text>
                    </View>
                  </View>

                  <Text style={styles.detailsTitle}>Data exchanged</Text>
                  <View style={styles.detailsWrap}>
                    {intg.details.map(d => (
                      <View key={d} style={styles.detailChip}>
                        <Text style={styles.detailChipText}>{d}</Text>
                      </View>
                    ))}
                  </View>

                  <TouchableOpacity style={styles.testBtn}>
                    <MaterialCommunityIcons name="access-point" size={14} color={Colors.teal} />
                    <Text style={styles.testBtnText}>Test connection</Text>
                  </TouchableOpacity>
                </View>
              )}
            </GlassCard>
          );
        })}

        {/* HL7 message log teaser */}
        <GlassCard style={styles.logCard}>
          <View style={styles.logHeader}>
            <MaterialCommunityIcons name="text-box-multiple-outline" size={17} color={Colors.blue} />
            <Text style={styles.logTitle}>Recent HL7 / FHIR Activity</Text>
          </View>
          {[
            { type: 'ORU^R01', desc: 'Lab result received — PT-0042', time: '2m ago',   color: Colors.teal  },
            { type: 'ADT^A01', desc: 'Patient admission — PT-0043',  time: '8m ago',   color: Colors.blue  },
            { type: '278',     desc: 'Prior auth approved — ref-001', time: '22m ago',  color: Colors.green },
            { type: 'ORM^O01', desc: 'Lab order sent — PT-0045',     time: '35m ago',  color: Colors.amber },
          ].map((log, i) => (
            <View key={i}>
              <View style={styles.logRow}>
                <View style={[styles.logTypeBadge, { backgroundColor: `${log.color}18` }]}>
                  <Text style={[styles.logType, { color: log.color }]}>{log.type}</Text>
                </View>
                <Text style={styles.logDesc}>{log.desc}</Text>
                <Text style={styles.logTime}>{log.time}</Text>
              </View>
              {i < 3 && <Divider />}
            </View>
          ))}
          <TouchableOpacity style={styles.viewAllBtn}>
            <Text style={styles.viewAllText}>View full message log →</Text>
          </TouchableOpacity>
        </GlassCard>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  fhirBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.teal}18`, borderWidth: 1, borderColor: `${Colors.teal}30`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  fhirText: { color: Colors.teal, fontSize: 11, fontWeight: '800', letterSpacing: 0.5 },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  summaryCard: { gap: Spacing.md },
  summaryTitle: { color: Colors.white, fontSize: 15, fontWeight: '700' },
  summaryRow: { flexDirection: 'row', alignItems: 'center' },
  summaryStat: { flex: 1, alignItems: 'center', gap: 3 },
  summaryVal: { fontSize: 28, fontWeight: '900' },
  summaryLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  summaryDivider: { width: 1, height: 40, backgroundColor: Colors.glassBorder },
  fhirNote: { flexDirection: 'row', gap: 6, alignItems: 'flex-start', backgroundColor: Colors.tealDim2, borderRadius: Radius.sm, padding: Spacing.xs + 2 },
  fhirNoteText: { color: Colors.gray400, fontSize: 11, flex: 1, lineHeight: 16 },
  catScroll: { gap: Spacing.xs, paddingBottom: 4 },
  catChip: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full },
  catChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  catText: { color: Colors.gray400, fontSize: 12 },
  catTextActive: { color: Colors.teal, fontWeight: '700' },
  intgCard: { gap: Spacing.sm },
  intgCardError: { borderColor: `${Colors.red}44` },
  intgHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  intgIconBg: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  intgName: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  intgCategory: { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  intgRight: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  intgDetails: { gap: Spacing.sm, paddingTop: Spacing.xs },
  intgDesc: { color: Colors.gray400, fontSize: 13, lineHeight: 19 },
  metaRow: { flexDirection: 'row', gap: Spacing.sm },
  metaItem: { flex: 1, gap: 2 },
  metaLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  metaVal: { color: Colors.white, fontSize: 12, fontWeight: '600' },
  detailsTitle: { color: Colors.gray400, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  detailsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  detailChip: { backgroundColor: Colors.navyLight, borderRadius: Radius.sm, paddingHorizontal: 8, paddingVertical: 3 },
  detailChipText: { color: Colors.gray400, fontSize: 11 },
  testBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}30`, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  testBtnText: { color: Colors.teal, fontSize: 12, fontWeight: '600' },
  logCard: { gap: Spacing.sm },
  logHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  logTitle: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  logRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xs + 2 },
  logTypeBadge: { borderRadius: Radius.sm, paddingHorizontal: 7, paddingVertical: 3, minWidth: 60, alignItems: 'center' },
  logType: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
  logDesc: { color: Colors.gray400, fontSize: 12, flex: 1 },
  logTime: { color: Colors.gray600, fontSize: 11 },
  viewAllBtn: {},
  viewAllText: { color: Colors.blue, fontSize: 13, fontWeight: '600', marginTop: 4 },
});
