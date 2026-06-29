import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, SafeAreaView, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, UrgencyIndicator, Button } from '../../components/ui';
import { useApp } from '../../context/AppContext';
import { api, TriageResult, ApprovedReport, CarePlan } from '../../services/api';

// ── Types ──────────────────────────────────────────────────────────────────────
interface Differential { condition: string; likelihood: number }
interface SOAPNote { subjective: string; objective: string; assessment: string; plan: string }
interface ICD10Code { code: string; description: string; type: 'primary' | 'secondary' }
interface CPTCode   { code: string; description: string; category: 'evaluation' | 'lab' | 'imaging' | 'procedure' }

const SOAP_CFG = {
  S: { label: 'S', full: 'Subjective',  sub: "Patient's perspective", color: '#4A9EFF' },
  O: { label: 'O', full: 'Objective',   sub: 'Measurable facts',      color: Colors.teal },
  A: { label: 'A', full: 'Assessment',  sub: 'Medical diagnosis',     color: Colors.amber },
  P: { label: 'P', full: 'Plan',        sub: 'Next steps',            color: Colors.green },
} as const;
type SOAPKey = keyof typeof SOAP_CFG;

interface EditState {
  summary: string; clinicalImpression: string; differentials: Differential[];
  recommendations: string[]; labsAndOrders: string[];
  specialistPrimary: string; specialistDept: string; specialistReason: string;
  specialistUrgency: string; specialistHandoff: string; specialistDisposition: string;
}

const URGENCY_COLOR: Record<string, string> = { STAT: Colors.red, ASAP: Colors.amber, Routine: Colors.green };
const ROUTE_COLOR:   Record<string, string> = { PO: Colors.teal, IV: Colors.red, IM: Colors.amber, SQ: Colors.blue, Topical: Colors.green, Inhaled: Colors.blue };

// ─────────────────────────────────────────────────────────────────────────────
// STAFF READ-ONLY VIEW
// ─────────────────────────────────────────────────────────────────────────────
function StaffPatientView({
  id, profile, soap, icd10, cpt, approvedReport, carePlan,
}: {
  id: string;
  profile: any;
  soap: SOAPNote | null;
  icd10: ICD10Code[];
  cpt: CPTCode[];
  approvedReport: ApprovedReport | null;
  carePlan: CarePlan | null;
}) {
  const router = useRouter();
  const isApproved = approvedReport?.approved === true;

  return (
    <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>

      {/* ── Patient card ── */}
      <GlassCard style={s.patientCard}>
        <View style={s.patientRow}>
          <View style={s.avatar}>
            <Text style={s.avatarText}>{profile?.initials ?? profile?.name?.[0] ?? '?'}</Text>
          </View>
          <View style={{ flex: 1, gap: 3 }}>
            <Text style={s.patientName}>{profile?.name ?? id}</Text>
            <Text style={s.patientMeta}>
              {[profile?.age != null ? `${profile.age} yrs` : null, profile?.gender, profile?.dob ? `DOB ${profile.dob}` : null].filter(Boolean).join(' · ')}
            </Text>
            <Text style={s.patientId}>{id}</Text>
          </View>
        </View>
        {profile?.conditions?.filter((c: any) => c.is_active).length > 0 && (
          <View style={s.conditionsRow}>
            {profile.conditions.filter((c: any) => c.is_active).map((c: any, i: number) => (
              <View key={i} style={s.conditionChip}>
                <View style={s.conditionDot} />
                <Text style={s.conditionChipText}>{c.name}</Text>
              </View>
            ))}
          </View>
        )}
      </GlassCard>

      {/* ── Approved Documents Section ── */}
      <View style={s.approvedDocsHeader}>
        <View style={s.approvedDocsIconWrap}>
          <MaterialCommunityIcons name="file-document-multiple-outline" size={18} color={Colors.teal} />
        </View>
        <Text style={s.approvedDocsTitle}>Approved Documents</Text>
        {isApproved && (
          <View style={s.approvedPill}>
            <MaterialCommunityIcons name="check-circle" size={11} color={Colors.teal} />
            <Text style={s.approvedPillText}>Approved</Text>
          </View>
        )}
      </View>

      {/* ── Approval stamp (shown only when approved) ── */}
      {isApproved ? (
        <View style={s.approvedBanner}>
          <View style={s.approvedCheck}>
            <MaterialCommunityIcons name="check-bold" size={20} color={Colors.navy} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.approvedBannerTitle}>Approved by Doctor</Text>
            <Text style={s.approvedBannerSub}>
              {approvedReport.approved_by ?? 'Clinician'}
              {approvedReport.approved_at ? `  ·  ${new Date(approvedReport.approved_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}` : ''}
            </Text>
          </View>
          {approvedReport.audit_id ? (
            <View style={s.auditBadge}><Text style={s.auditText}>#{approvedReport.audit_id}</Text></View>
          ) : null}
        </View>
      ) : (
        <View style={s.pendingReviewBanner}>
          <MaterialCommunityIcons name="clock-alert-outline" size={16} color={Colors.amber} />
          <Text style={s.pendingReviewText}>Pending doctor approval — AI-generated data shown below</Text>
        </View>
      )}

      {/* ── Clinician note (only when approved) ── */}
      {isApproved && approvedReport.clinician_note ? (
        <GlassCard style={[s.noteCard, { borderLeftColor: Colors.teal }]}>
          <View style={s.noteCardHeader}>
            <MaterialCommunityIcons name="pencil-outline" size={14} color={Colors.teal} />
            <Text style={[s.noteCardTitle, { color: Colors.teal }]}>Doctor's Note</Text>
          </View>
          <Text style={s.noteCardBody}>{approvedReport.clinician_note}</Text>
        </GlassCard>
      ) : null}

      {/* ── SOAP Note ── */}
      {soap ? (
        <>
          <View style={s.sectionDivider}>
            <View style={s.sectionLine} />
            <Text style={s.sectionDividerText}>CLINICAL DIAGNOSIS</Text>
            <View style={s.sectionLine} />
          </View>

          {(Object.keys(SOAP_CFG) as SOAPKey[]).map(key => {
            const cfg = SOAP_CFG[key];
            const fieldMap: Record<SOAPKey, keyof SOAPNote> = { S: 'subjective', O: 'objective', A: 'assessment', P: 'plan' };
            const text = soap[fieldMap[key]];
            if (!text) return null;
            return (
              <GlassCard key={key} style={[s.soapCard, { borderLeftColor: cfg.color, borderLeftWidth: 4 }]}>
                <View style={s.soapHeader}>
                  <View style={[s.soapBadge, { backgroundColor: cfg.color }]}>
                    <Text style={s.soapBadgeLetter}>{cfg.label}</Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[s.soapTitle, { color: cfg.color }]}>{cfg.full}</Text>
                    <Text style={s.soapSub}>{cfg.sub}</Text>
                  </View>
                </View>
                <Text style={s.soapBody}>{text}</Text>
              </GlassCard>
            );
          })}
        </>
      ) : null}

      {/* ── ICD-10 Codes ── */}
      {icd10.length > 0 && (
        <>
          <View style={s.sectionDivider}>
            <View style={s.sectionLine} />
            <Text style={s.sectionDividerText}>ICD-10 CODES</Text>
            <View style={s.sectionLine} />
          </View>
          <GlassCard style={{ gap: Spacing.md }}>
            {icd10.filter(c => c.type === 'primary').length > 0 && (
              <View style={{ gap: 6 }}>
                <Text style={s.codeGroupLabel}>PRIMARY DIAGNOSIS</Text>
                {icd10.filter(c => c.type === 'primary').map((c, i) => (
                  <View key={i} style={[s.codeRow, { borderColor: `${Colors.amber}25` }]}>
                    <View style={[s.codeBadge, { backgroundColor: `${Colors.amber}18` }]}>
                      <Text style={[s.codeTiny, { color: Colors.amber }]}>Dx</Text>
                      <Text style={[s.codeNum, { color: Colors.amber }]}>{c.code}</Text>
                    </View>
                    <Text style={s.codeDesc}>{c.description}</Text>
                  </View>
                ))}
              </View>
            )}
            {icd10.filter(c => c.type === 'secondary').length > 0 && (
              <View style={{ gap: 6 }}>
                <Text style={s.codeGroupLabel}>SECONDARY / RULE-OUT</Text>
                {icd10.filter(c => c.type === 'secondary').map((c, i) => (
                  <View key={i} style={[s.codeRow, { borderColor: `${Colors.blue}25` }]}>
                    <View style={[s.codeBadge, { backgroundColor: `${Colors.blue}18` }]}>
                      <Text style={[s.codeTiny, { color: Colors.blue }]}>Dx</Text>
                      <Text style={[s.codeNum, { color: Colors.blue }]}>{c.code}</Text>
                    </View>
                    <Text style={s.codeDesc}>{c.description}</Text>
                  </View>
                ))}
              </View>
            )}
          </GlassCard>
        </>
      )}

      {/* ── CPT Codes ── */}
      {cpt.length > 0 && (
        <>
          <View style={s.sectionDivider}>
            <View style={s.sectionLine} />
            <Text style={s.sectionDividerText}>CPT CODES</Text>
            <View style={s.sectionLine} />
          </View>
          <GlassCard style={{ gap: Spacing.md }}>
            {(['evaluation', 'lab', 'imaging', 'procedure'] as const).map(cat => {
              const catColors = { evaluation: Colors.teal, lab: Colors.green, imaging: Colors.blue, procedure: Colors.amber };
              const catLabels = { evaluation: 'E/M', lab: 'Lab', imaging: 'Img', procedure: 'Proc' };
              const items = cpt.filter(c => c.category === cat);
              if (!items.length) return null;
              const color = catColors[cat];
              return (
                <View key={cat} style={{ gap: 6 }}>
                  <Text style={s.codeGroupLabel}>{cat.toUpperCase()}</Text>
                  {items.map((c, i) => (
                    <View key={i} style={[s.codeRow, { borderColor: `${color}25` }]}>
                      <View style={[s.codeBadge, { backgroundColor: `${color}18` }]}>
                        <Text style={[s.codeTiny, { color }]}>{catLabels[cat]}</Text>
                        <Text style={[s.codeNum, { color }]}>{c.code}</Text>
                      </View>
                      <Text style={s.codeDesc}>{c.description}</Text>
                    </View>
                  ))}
                </View>
              );
            })}
          </GlassCard>
        </>
      )}

      {/* ── Care Plan ── */}
      {carePlan?.exists && (
            <>
              <View style={s.sectionDivider}>
                <View style={s.sectionLine} />
                <Text style={s.sectionDividerText}>CARE PLAN</Text>
                <View style={s.sectionLine} />
              </View>

              {/* Epic/SIS banner */}
              <View style={s.epicBanner}>
                <MaterialCommunityIcons name="hospital-building" size={16} color={Colors.blue} />
                <Text style={s.epicBannerText}>Enter the following into Epic / SIS before patient discharge</Text>
              </View>

              {/* Labs */}
              {carePlan.labs && carePlan.labs.length > 0 && (
                <GlassCard style={{ gap: Spacing.sm }}>
                  <View style={s.cpHeader}>
                    <MaterialCommunityIcons name="test-tube" size={14} color={Colors.teal} />
                    <Text style={s.cpHeaderText}>Labs Ordered</Text>
                  </View>
                  {carePlan.labs.map((lab, i) => {
                    const uc = URGENCY_COLOR[lab.urgency] ?? Colors.gray400;
                    return (
                      <View key={i} style={[s.cpLabRow, i > 0 && { borderTopWidth: 1, borderTopColor: Colors.glassBorder, paddingTop: Spacing.sm }]}>
                        <View style={[s.urgencyBadge, { backgroundColor: `${uc}18`, borderColor: `${uc}44` }]}>
                          <Text style={[s.urgencyText, { color: uc }]}>{lab.urgency}</Text>
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={s.cpItemName}>{lab.name}</Text>
                          <Text style={s.cpItemMeta}>{lab.timing}</Text>
                          {lab.notes ? <Text style={s.cpItemNote}>{lab.notes}</Text> : null}
                        </View>
                      </View>
                    );
                  })}
                </GlassCard>
              )}

              {/* Medications */}
              {carePlan.medications && carePlan.medications.length > 0 && carePlan.medications.map((med, i) => {
                const rc = ROUTE_COLOR[med.route] ?? Colors.teal;
                return (
                  <GlassCard key={i} style={s.medCard}>
                    <View style={s.medHeader}>
                      <MaterialCommunityIcons name="pill" size={15} color={Colors.teal} />
                      <Text style={s.medName}>{med.name}</Text>
                    </View>
                    <View style={s.medChips}>
                      <View style={s.doseChip}><Text style={s.doseChipText}>{med.dose}</Text></View>
                      <View style={s.doseChip}><Text style={s.doseChipText}>{med.frequency}</Text></View>
                      <View style={[s.routeChip, { backgroundColor: `${rc}18`, borderColor: `${rc}44` }]}>
                        <Text style={[s.routeChipText, { color: rc }]}>{med.route}</Text>
                      </View>
                    </View>
                    {med.duration ? (
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
                        <MaterialCommunityIcons name="calendar-range" size={12} color={Colors.gray400} />
                        <Text style={s.cpItemMeta}>Duration: {med.duration}</Text>
                      </View>
                    ) : null}
                    {med.notes ? (
                      <View style={s.medNoteBox}><Text style={s.medNoteText}>{med.notes}</Text></View>
                    ) : null}
                  </GlassCard>
                );
              })}

              {/* Instructions */}
              {carePlan.instructions ? (
                <GlassCard style={[s.infoCard, { borderLeftColor: Colors.blue }]}>
                  <View style={s.cpHeader}>
                    <MaterialCommunityIcons name="clipboard-list-outline" size={14} color={Colors.blue} />
                    <Text style={[s.cpHeaderText, { color: Colors.blue }]}>Instructions</Text>
                  </View>
                  <Text style={s.cpBodyText}>{carePlan.instructions}</Text>
                </GlassCard>
              ) : null}

              {/* Follow-up */}
              {carePlan.follow_up ? (
                <GlassCard style={[s.infoCard, { borderLeftColor: Colors.teal }]}>
                  <View style={s.cpHeader}>
                    <MaterialCommunityIcons name="calendar-clock" size={14} color={Colors.teal} />
                    <Text style={[s.cpHeaderText, { color: Colors.teal }]}>Follow-Up</Text>
                  </View>
                  <Text style={s.cpBodyText}>{carePlan.follow_up}</Text>
                </GlassCard>
              ) : null}

              {/* Diet */}
              {carePlan.diet ? (
                <GlassCard style={[s.infoCard, { borderLeftColor: Colors.green }]}>
                  <View style={s.cpHeader}>
                    <MaterialCommunityIcons name="food-apple-outline" size={14} color={Colors.green} />
                    <Text style={[s.cpHeaderText, { color: Colors.green }]}>Diet</Text>
                  </View>
                  <Text style={s.cpBodyText}>{carePlan.diet}</Text>
                </GlassCard>
              ) : null}

              {/* Activity */}
              {carePlan.activity ? (
                <GlassCard style={[s.infoCard, { borderLeftColor: Colors.amber }]}>
                  <View style={s.cpHeader}>
                    <MaterialCommunityIcons name="run" size={14} color={Colors.amber} />
                    <Text style={[s.cpHeaderText, { color: Colors.amber }]}>Activity</Text>
                  </View>
                  <Text style={s.cpBodyText}>{carePlan.activity}</Text>
                </GlassCard>
              ) : null}

              {/* Approved at */}
              {carePlan.approved_at ? (
                <Text style={s.cpApprovedAt}>
                  Care plan approved {new Date(carePlan.approved_at).toLocaleString()} by {carePlan.doctor_id ?? 'Doctor'}
                </Text>
              ) : null}
            </>
          )}

      {/* ── Care plan not yet created ── */}
      {!carePlan?.exists && (
        <>
          <View style={s.sectionDivider}>
            <View style={s.sectionLine} />
            <Text style={s.sectionDividerText}>CARE PLAN</Text>
            <View style={s.sectionLine} />
          </View>
          <GlassCard style={s.noPlanCard}>
            <MaterialCommunityIcons name="clipboard-plus-outline" size={32} color={Colors.gray600} />
            <Text style={s.noPlanTitle}>Care Plan Not Yet Created</Text>
            <Text style={s.noPlanBody}>
              The doctor has approved the diagnosis. A care plan will appear here once the doctor creates and approves it.
            </Text>
          </GlassCard>
        </>
      )}

      <View style={{ height: Spacing.xxl }} />
    </ScrollView>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DOCTOR EDIT LIST
// ─────────────────────────────────────────────────────────────────────────────
function EditableList({ items, onUpdate, onRemove, onAdd, placeholder, editMode, itemColor = Colors.white }: {
  items: string[]; onUpdate: (i: number, v: string) => void; onRemove: (i: number) => void;
  onAdd: () => void; placeholder: string; editMode: boolean; itemColor?: string;
}) {
  return (
    <View style={{ gap: 6 }}>
      {items.map((item, i) => (
        <View key={i} style={ds.editListRow}>
          {editMode ? (
            <>
              <TextInput style={[ds.inlineInput, { flex: 1 }]} value={item} onChangeText={v => onUpdate(i, v)}
                placeholder={placeholder} placeholderTextColor={Colors.gray600} multiline />
              <TouchableOpacity onPress={() => onRemove(i)} style={ds.removeBtn}>
                <MaterialCommunityIcons name="close-circle" size={18} color={Colors.red} />
              </TouchableOpacity>
            </>
          ) : (
            <Text style={[ds.listItemText, { color: itemColor }]}>• {item}</Text>
          )}
        </View>
      ))}
      {editMode && (
        <TouchableOpacity style={ds.addBtn} onPress={onAdd}>
          <MaterialCommunityIcons name="plus-circle-outline" size={16} color={Colors.teal} />
          <Text style={ds.addBtnText}>Add item</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN SCREEN
// ─────────────────────────────────────────────────────────────────────────────
export default function PatientDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id?: string }>();
  const { clinicianId, isDoctor } = useApp();

  const [patient, setPatient]     = useState<TriageResult | null>(null);
  const [profile, setProfile]     = useState<any | null>(null);
  const [loading, setLoading]     = useState(true);
  const [editMode, setEditMode]   = useState(false);
  const [note, setNote]           = useState('');
  const [overrideUrgency, setOverrideUrgency] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [approved, setApproved]   = useState(false);
  const [edits, setEdits]         = useState<EditState | null>(null);
  const [hasEdits, setHasEdits]   = useState(false);
  const [soap, setSOAP]           = useState<SOAPNote | null>(null);
  const [icd10, setICD10]         = useState<ICD10Code[]>([]);
  const [cptCodes, setCPT]        = useState<CPTCode[]>([]);
  const [soapEditMode, setSOAPEditMode] = useState(false);
  const [soapEdits, setSOAPEdits] = useState<SOAPNote | null>(null);
  const [approvedReport, setApprovedReport] = useState<ApprovedReport | null>(null);
  const [carePlan, setCarePlan]   = useState<CarePlan | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.allSettled([
      api.getClinicianTriage(id).then((p: any) => {
        setPatient(p);
        const diag = p.diagnostics ?? {};
        const soapData: SOAPNote | null = diag.soap_note ?? p.soap_note ?? null;
        setSOAP(soapData);
        setSOAPEdits(soapData ? { ...soapData } : null);
        setICD10(diag.icd10_codes ?? p.icd10_codes ?? []);
        setCPT(diag.cpt_codes ?? p.cpt_codes ?? []);
        setEdits({
          summary:              p.summary ?? '',
          clinicalImpression:   p.clinical_reasoning ?? '',
          differentials:        (p.differentials ?? []).map((d: any) => ({ ...d })),
          recommendations:      [...(p.recommendations ?? [])],
          labsAndOrders:        [...(p.labs_ordered ?? []), ...(p.imaging ?? [])],
          specialistPrimary:    p.specialist_assignment?.primary_specialist ?? '',
          specialistDept:       p.specialist_assignment?.department ?? '',
          specialistReason:     p.specialist_assignment?.reason ?? '',
          specialistUrgency:    p.specialist_assignment?.urgency_for_specialist ?? '',
          specialistHandoff:    p.specialist_assignment?.handoff_instructions ?? '',
          specialistDisposition:p.specialist_assignment?.estimated_disposition ?? '',
        });
      }),
      api.getPatientProfile(id).then(setProfile),
      api.getApprovedReport(id).then(r => {
        setApprovedReport(r);
        if (r.approved) {
          if (r.soap_note) { setSOAP(prev => prev ?? r.soap_note!); setSOAPEdits(prev => prev ?? { ...r.soap_note! }); }
          if (r.icd10_codes?.length) setICD10(prev => prev.length ? prev : r.icd10_codes!);
          if (r.cpt_codes?.length)   setCPT(prev   => prev.length ? prev : r.cpt_codes!);
        }
      }).catch(() => {}),
      api.getCarePlan(id).then(cp => { if (cp.exists) setCarePlan(cp); }).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [id]);

  const updateEdits = (patch: Partial<EditState>) => { setEdits(prev => prev ? { ...prev, ...patch } : prev); setHasEdits(true); };

  const toggleEditMode = () => {
    if (editMode && hasEdits) {
      Alert.alert('Keep changes?', 'Your edits will be included when you approve the report.', [{ text: 'OK', onPress: () => setEditMode(false) }]);
    } else { setEditMode(v => !v); }
  };

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    const editPayload = hasEdits && edits ? {
      summary: edits.summary || undefined, clinical_impression: edits.clinicalImpression || undefined,
      differentials: edits.differentials.filter(d => d.condition),
      recommendations: edits.recommendations.filter(Boolean),
      labs_and_orders: edits.labsAndOrders.filter(Boolean),
      specialist_primary: edits.specialistPrimary || undefined, specialist_department: edits.specialistDept || undefined,
      specialist_reason: edits.specialistReason || undefined, specialist_urgency: edits.specialistUrgency || undefined,
      specialist_handoff: edits.specialistHandoff || undefined, specialist_disposition: edits.specialistDisposition || undefined,
      soap_subjective: soapEdits?.subjective || undefined, soap_objective: soapEdits?.objective || undefined,
      soap_assessment: soapEdits?.assessment || undefined, soap_plan: soapEdits?.plan || undefined,
      icd10_codes: icd10.length > 0 ? icd10 : undefined, cpt_codes: cptCodes.length > 0 ? cptCodes : undefined,
    } : undefined;
    setApproved(true); setApproving(false);
    api.approveTriage(id, clinicianId, note || undefined, overrideUrgency || undefined, editPayload).catch(() => {});
  };

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color={Colors.teal} size="large" />
        <Text style={{ color: Colors.gray400, marginTop: Spacing.md }}>Loading patient data…</Text>
      </SafeAreaView>
    );
  }

  const p = patient;
  const urgency = (overrideUrgency || p?.urgency || 'medium') as any;
  const pathway = p?.care_pathway ?? 'Urgent Care';

  // ── STAFF VIEW ───────────────────────────────────────────────────────────────
  if (!isDoctor) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
        <View style={s.header}>
          <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
            <Ionicons name="arrow-back" size={22} color={Colors.white} />
          </TouchableOpacity>
          <View style={{ flex: 1, alignItems: 'center' }}>
            <Text style={s.headerTitle}>{profile?.name ?? id ?? 'Patient'}</Text>
            <Text style={s.headerSub}>Staff View — Read Only</Text>
          </View>
          <View style={{ width: 40 }} />
        </View>
        <StaffPatientView
          id={id!}
          profile={profile}
          soap={soap}
          icd10={icd10}
          cpt={cptCodes}
          approvedReport={approvedReport}
          carePlan={carePlan}
        />
      </SafeAreaView>
    );
  }

  // ── DOCTOR APPROVAL CONFIRMED ────────────────────────────────────────────────
  if (approved) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
        <View style={ds.header}>
          <TouchableOpacity onPress={() => router.replace('/staff/dashboard' as any)} style={ds.backBtn}>
            <Ionicons name="arrow-back" size={22} color={Colors.white} />
          </TouchableOpacity>
          <Text style={ds.headerTitle}>Diagnosis Approved</Text>
          <View style={{ width: 40 }} />
        </View>
        <View style={ds.approvedContainer}>
          <MaterialCommunityIcons name="check-circle" size={72} color={Colors.teal} />
          <Text style={ds.approvedTitle}>Diagnosis Approved</Text>
          <Text style={ds.approvedText}>
            {profile?.name ?? id} — diagnosis visible to nursing staff.{'\n'}
            {hasEdits ? 'Clinician edits saved.\n' : ''}Audit log entry created.
          </Text>

          <Button
            label="Create Care Plan Now"
            onPress={() => router.replace({ pathname: '/staff/care-plan' as any, params: { id } })}
            size="lg" style={{ width: '100%' }}
          />
          <TouchableOpacity onPress={() => router.replace('/staff/dashboard' as any)} style={ds.laterBtn}>
            <Text style={ds.laterBtnText}>Do this later from dashboard</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ── DOCTOR VIEW ──────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={ds.header}>
        <TouchableOpacity onPress={() => router.back()} style={ds.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={ds.headerTitle}>{profile?.name ?? id ?? 'Patient'}</Text>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.sm }}>
          {hasEdits && !editMode && (
            <View style={ds.editedBadge}><Text style={ds.editedBadgeText}>EDITED</Text></View>
          )}
          <TouchableOpacity style={[ds.editToggleBtn, editMode && ds.editToggleBtnActive]} onPress={toggleEditMode}>
            <MaterialCommunityIcons name={editMode ? 'check' : 'pencil-outline'} size={16} color={editMode ? Colors.navy : Colors.teal} />
            <Text style={[ds.editToggleText, editMode && { color: Colors.navy }]}>{editMode ? 'Done' : 'Edit'}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {editMode && (
        <View style={ds.editBanner}>
          <MaterialCommunityIcons name="pencil" size={14} color={Colors.amber} />
          <Text style={ds.editBannerText}>Edit mode — changes will override the AI output in the patient report</Text>
        </View>
      )}

      <ScrollView contentContainerStyle={ds.scroll} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">

        {/* Patient info */}
        <GlassCard>
          <View style={ds.patientRow}>
            <View style={ds.patientAvatar}>
              {profile?.initials
                ? <Text style={ds.patientInitials}>{profile.initials}</Text>
                : <MaterialCommunityIcons name="account" size={28} color={Colors.teal} />}
            </View>
            <View style={{ flex: 1 }}>
              <Text style={ds.patientName}>{profile?.name ?? id}</Text>
              {profile && <Text style={ds.patientMeta}>{[profile.age != null ? `${profile.age} yrs` : '', profile.gender, profile.dob ? `DOB: ${profile.dob}` : ''].filter(Boolean).join(' · ')}</Text>}
              <Text style={ds.patientSubId}>{id}</Text>
              <Text style={ds.pathwayLabel}>Pathway: <Text style={{ color: Colors.blue }}>{pathway}</Text></Text>
              {p?.sepsis_concern && (
                <View style={ds.sepsisAlert}>
                  <MaterialCommunityIcons name="alert" size={13} color={Colors.red} />
                  <Text style={ds.sepsisText}>Sepsis concern flagged</Text>
                </View>
              )}
            </View>
            <UrgencyIndicator level={urgency} />
          </View>
          {profile?.conditions?.filter((c: any) => c.is_active).length > 0 && (
            <View style={ds.conditionsRow}>
              {profile.conditions.filter((c: any) => c.is_active).map((c: any, i: number) => (
                <View key={i} style={ds.conditionChip}>
                  <View style={ds.conditionDot} />
                  <Text style={ds.conditionChipText}>{c.name}</Text>
                </View>
              ))}
            </View>
          )}
        </GlassCard>

        {/* SOAP Note */}
        {(soap || soapEdits) && (
          <GlassCard style={soapEditMode ? ds.editableCard : undefined}>
            <View style={ds.cardHeader}>
              <MaterialCommunityIcons name="clipboard-text-outline" size={16} color={Colors.teal} />
              <Text style={ds.cardTitle}>SOAP Note</Text>
              <TouchableOpacity style={[ds.soapEditBtn, soapEditMode && ds.soapEditBtnActive]} onPress={() => setSOAPEditMode(v => !v)}>
                <MaterialCommunityIcons name={soapEditMode ? 'check' : 'pencil-outline'} size={13} color={soapEditMode ? Colors.navy : Colors.teal} />
                <Text style={[ds.soapEditBtnText, soapEditMode && { color: Colors.navy }]}>{soapEditMode ? 'Done' : 'Edit'}</Text>
              </TouchableOpacity>
            </View>
            {(Object.keys(SOAP_CFG) as SOAPKey[]).map(key => {
              const cfg = SOAP_CFG[key];
              const fieldMap: Record<SOAPKey, keyof SOAPNote> = { S: 'subjective', O: 'objective', A: 'assessment', P: 'plan' };
              const field = fieldMap[key];
              const value = soapEdits?.[field] ?? soap?.[field] ?? '';
              return (
                <View key={key} style={[ds.soapSection, { borderLeftColor: cfg.color }]}>
                  <View style={ds.soapSectionHeader}>
                    <View style={[ds.soapBadge, { backgroundColor: cfg.color }]}>
                      <Text style={ds.soapBadgeLetter}>{cfg.label}</Text>
                    </View>
                    <View>
                      <Text style={[ds.soapSectionTitle, { color: cfg.color }]}>{cfg.full}</Text>
                      <Text style={ds.soapSectionSub}>{cfg.sub}</Text>
                    </View>
                  </View>
                  {soapEditMode ? (
                    <TextInput
                      style={ds.soapTextInput} value={value} multiline textAlignVertical="top"
                      placeholderTextColor={Colors.gray600} placeholder={`Enter ${cfg.full.toLowerCase()} notes…`}
                      onChangeText={v => { setSOAPEdits(prev => ({ ...(prev ?? { subjective: '', objective: '', assessment: '', plan: '' }), [field]: v })); setHasEdits(true); }}
                    />
                  ) : (
                    <Text style={ds.soapText}>{value || '—'}</Text>
                  )}
                </View>
              );
            })}
          </GlassCard>
        )}

        {/* ICD-10 */}
        {icd10.length > 0 && (
          <GlassCard>
            <View style={ds.cardHeader}>
              <MaterialCommunityIcons name="barcode-scan" size={16} color={Colors.amber} />
              <Text style={ds.cardTitle}>ICD-10 Codes</Text>
            </View>
            {['primary', 'secondary'].map(type => {
              const items = icd10.filter(c => c.type === type);
              if (!items.length) return null;
              const color = type === 'primary' ? Colors.amber : Colors.blue;
              return (
                <View key={type} style={{ marginBottom: Spacing.sm }}>
                  <Text style={ds.codeGroupLabel}>{type === 'primary' ? 'PRIMARY DIAGNOSIS' : 'SECONDARY / RULE-OUT'}</Text>
                  {items.map((c, i) => (
                    <View key={i} style={[ds.codeRow, { borderColor: `${color}25` }]}>
                      <View style={[ds.codeBadge, { backgroundColor: `${color}18` }]}>
                        <Text style={[ds.codeTiny, { color }]}>Dx</Text>
                        <Text style={[ds.codeNum, { color }]}>{c.code}</Text>
                      </View>
                      <Text style={ds.codeDesc}>{c.description}</Text>
                    </View>
                  ))}
                </View>
              );
            })}
          </GlassCard>
        )}

        {/* CPT */}
        {cptCodes.length > 0 && (
          <GlassCard>
            <View style={ds.cardHeader}>
              <MaterialCommunityIcons name="receipt" size={16} color={Colors.green} />
              <Text style={ds.cardTitle}>CPT Codes</Text>
            </View>
            {(['evaluation', 'lab', 'imaging', 'procedure'] as const).map(cat => {
              const catColors = { evaluation: Colors.teal, lab: Colors.green, imaging: Colors.blue, procedure: Colors.amber };
              const catLabels = { evaluation: 'E&M', lab: 'LAB', imaging: 'IMG', procedure: 'PROC' };
              const items = cptCodes.filter(c => c.category === cat);
              if (!items.length) return null;
              const color = catColors[cat];
              return (
                <View key={cat} style={{ marginBottom: Spacing.sm }}>
                  <Text style={ds.codeGroupLabel}>{cat.toUpperCase()}</Text>
                  {items.map((c, i) => (
                    <View key={i} style={[ds.codeRow, { borderColor: `${color}25` }]}>
                      <View style={[ds.codeBadge, { backgroundColor: `${color}18` }]}>
                        <Text style={[ds.codeTiny, { color }]}>{catLabels[cat]}</Text>
                        <Text style={[ds.codeNum, { color }]}>{c.code}</Text>
                      </View>
                      <Text style={ds.codeDesc}>{c.description}</Text>
                    </View>
                  ))}
                </View>
              );
            })}
          </GlassCard>
        )}

        {/* Specialist */}
        {edits && (
          <GlassCard style={[{ borderColor: `${Colors.blue}33` }, editMode && ds.editableCard]}>
            <View style={ds.cardHeader}>
              <MaterialCommunityIcons name="doctor" size={16} color={Colors.blue} />
              <Text style={ds.cardTitle}>Specialist Assignment</Text>
              {editMode && <MaterialCommunityIcons name="pencil" size={13} color={Colors.amber} />}
            </View>
            {editMode ? (
              <View style={{ gap: Spacing.sm }}>
                {[
                  { label: 'Primary Specialist', key: 'specialistPrimary', ph: 'e.g. Cardiologist' },
                  { label: 'Department', key: 'specialistDept', ph: 'e.g. Cardiology' },
                  { label: 'Reason', key: 'specialistReason', ph: 'Reason for referral' },
                  { label: 'Urgency', key: 'specialistUrgency', ph: 'e.g. WITHIN_4H' },
                  { label: 'Handoff Instructions', key: 'specialistHandoff', ph: 'Instructions for specialist' },
                  { label: 'Disposition', key: 'specialistDisposition', ph: 'e.g. ADMIT / OBSERVE' },
                ].map(({ label, key, ph }) => (
                  <View key={key} style={{ gap: 3 }}>
                    <Text style={ds.fieldLabel}>{label}</Text>
                    <TextInput style={ds.inlineInput} value={(edits as any)[key]}
                      onChangeText={v => updateEdits({ [key]: v } as any)}
                      placeholder={ph} placeholderTextColor={Colors.gray600}
                      multiline={key === 'specialistReason' || key === 'specialistHandoff'} />
                  </View>
                ))}
              </View>
            ) : (
              <Text style={ds.specialistDept}>{edits.specialistDept || p?.specialist_assignment?.department || '—'}</Text>
            )}
          </GlassCard>
        )}

        {/* Clinician review */}
        <GlassCard style={ds.reviewCard}>
          <View style={ds.cardHeader}>
            <MaterialCommunityIcons name="shield-check-outline" size={16} color={Colors.teal} />
            <Text style={ds.cardTitle}>Clinician Review</Text>
          </View>
          {hasEdits && (
            <View style={ds.editSummaryBanner}>
              <MaterialCommunityIcons name="pencil-check" size={14} color={Colors.amber} />
              <Text style={ds.editSummaryText}>Report edited — your changes will be included.</Text>
            </View>
          )}
          <Text style={ds.overrideLabel}>Override urgency (optional)</Text>
          <View style={ds.overrideChips}>
            {(['low', 'medium', 'high', 'critical'] as const).map(u => (
              <TouchableOpacity key={u} style={[ds.overrideChip, overrideUrgency === u && ds.overrideChipActive]}
                onPress={() => setOverrideUrgency(overrideUrgency === u ? null : u)}>
                <Text style={[ds.overrideChipText, overrideUrgency === u && { color: Colors.white }]}>{u.charAt(0).toUpperCase() + u.slice(1)}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={[ds.overrideLabel, { marginTop: Spacing.sm }]}>Clinical notes</Text>
          <TextInput style={ds.noteInput} value={note} onChangeText={setNote}
            placeholder="Add clinical notes for the record..." placeholderTextColor={Colors.gray600}
            multiline numberOfLines={3} textAlignVertical="top" />
          <Button
            label={approving ? 'Approving…' : hasEdits ? (overrideUrgency ? `Approve Edits as ${overrideUrgency.toUpperCase()}` : 'Approve Edited Report') : overrideUrgency ? `Approve as ${overrideUrgency.toUpperCase()}` : 'Approve AI Recommendation'}
            onPress={handleApprove} loading={approving} size="lg" style={{ marginTop: Spacing.xs }}
          />
          <Button
            label="Escalate to Emergency"
            onPress={() => Alert.alert('Escalate', 'This will flag the patient as CRITICAL and alert the emergency team.', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Escalate', style: 'destructive', onPress: () => setOverrideUrgency('critical') },
            ])}
            variant="danger" size="md"
          />
          {patient?.triage_decision && (
            <Button label="View / Edit Care Plan"
              onPress={() => router.push({ pathname: '/staff/care-plan' as any, params: { id } })}
              size="md"
            />
          )}
        </GlassCard>
      </ScrollView>
    </SafeAreaView>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// STAFF VIEW STYLES  (prefix: s.)
// ─────────────────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  header:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn:    { width: 40, height: 40, justifyContent: 'center' },
  headerTitle:{ color: Colors.white, fontSize: 16, fontWeight: '700' },
  headerSub:  { color: Colors.gray600, fontSize: 10, fontWeight: '600', letterSpacing: 0.5 },
  scroll:     { padding: Spacing.lg, gap: Spacing.md },

  // Patient card
  patientCard:      { gap: Spacing.md },
  patientRow:       { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatar:           { width: 52, height: 52, borderRadius: 26, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  avatarText:       { color: Colors.navy, fontWeight: '900', fontSize: 20 },
  patientName:      { color: Colors.white, fontSize: 16, fontWeight: '800' },
  patientMeta:      { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  patientId:        { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  conditionsRow:    { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs, paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.glassBorder },
  conditionChip:    { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.red}12`, borderWidth: 1, borderColor: `${Colors.red}33`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  conditionDot:     { width: 5, height: 5, borderRadius: 2.5, backgroundColor: Colors.red },
  conditionChipText:{ color: Colors.red, fontSize: 11, fontWeight: '600' },

  // Approved Documents header
  approvedDocsHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.xs },
  approvedDocsIconWrap: { width: 32, height: 32, borderRadius: 10, backgroundColor: `${Colors.teal}18`, borderWidth: 1, borderColor: `${Colors.teal}33`, alignItems: 'center', justifyContent: 'center' },
  approvedDocsTitle: { color: Colors.white, fontSize: 15, fontWeight: '800', flex: 1 },
  approvedPill: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.teal}18`, borderWidth: 1, borderColor: `${Colors.teal}44`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  approvedPillText: { color: Colors.teal, fontSize: 11, fontWeight: '700' },

  // Pending review banner (for staff when not yet approved)
  pendingReviewBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.amber}10`, borderWidth: 1, borderColor: `${Colors.amber}33`, borderRadius: Radius.md, padding: Spacing.md },
  pendingReviewText: { color: Colors.amber, fontSize: 12, flex: 1, lineHeight: 18 },

  // Banners
  approvedBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, backgroundColor: `${Colors.teal}14`, borderWidth: 1, borderColor: `${Colors.teal}33`, borderRadius: Radius.md, padding: Spacing.md },
  approvedCheck:  { width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.teal, alignItems: 'center', justifyContent: 'center' },
  approvedBannerTitle: { color: Colors.white, fontWeight: '800', fontSize: 14 },
  approvedBannerSub:   { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  auditBadge:     { backgroundColor: `${Colors.gray600}25`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3 },
  auditText:      { color: Colors.gray600, fontSize: 10, fontWeight: '700' },

  // Doctor note
  noteCard:       { borderLeftWidth: 4, gap: Spacing.xs },
  noteCardHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  noteCardTitle:  { fontSize: 13, fontWeight: '700' },
  noteCardBody:   { color: Colors.gray400, fontSize: 13, lineHeight: 20, fontStyle: 'italic' },

  // Section divider
  sectionDivider:     { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: Spacing.xs },
  sectionLine:        { flex: 1, height: 1, backgroundColor: Colors.glassBorder },
  sectionDividerText: { color: Colors.gray600, fontSize: 10, fontWeight: '800', letterSpacing: 1.2 },

  // SOAP
  soapCard:       { gap: Spacing.sm },
  soapHeader:     { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  soapBadge:      { width: 30, height: 30, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  soapBadgeLetter:{ color: Colors.navy, fontSize: 15, fontWeight: '900' },
  soapTitle:      { fontSize: 14, fontWeight: '800' },
  soapSub:        { color: Colors.gray600, fontSize: 11 },
  soapBody:       { color: Colors.gray400, fontSize: 13, lineHeight: 22, paddingLeft: Spacing.xs },

  // Codes
  codeGroupLabel: { color: Colors.gray600, fontSize: 9, fontWeight: '800', letterSpacing: 1, marginBottom: 5 },
  codeRow:        { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, borderWidth: 1, borderRadius: Radius.sm, padding: Spacing.sm, marginBottom: 5 },
  codeBadge:      { borderRadius: 6, paddingHorizontal: 5, paddingVertical: 3, alignItems: 'center', minWidth: 44 },
  codeTiny:       { fontSize: 8, fontWeight: '800', letterSpacing: 0.5 },
  codeNum:        { fontSize: 12, fontWeight: '900' },
  codeDesc:       { color: Colors.gray400, fontSize: 12, lineHeight: 17, flex: 1 },

  // Epic banner
  epicBanner:     { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.blue}12`, borderWidth: 1, borderColor: `${Colors.blue}33`, borderRadius: Radius.md, padding: Spacing.md },
  epicBannerText: { color: Colors.blue, fontSize: 13, fontWeight: '600', flex: 1, lineHeight: 19 },

  // Care plan
  cpHeader:    { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: Spacing.xs },
  cpHeaderText:{ color: Colors.teal, fontSize: 13, fontWeight: '700' },
  cpLabRow:    { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  urgencyBadge:{ borderWidth: 1, borderRadius: Radius.sm, paddingHorizontal: 7, paddingVertical: 3, alignItems: 'center', justifyContent: 'center' },
  urgencyText: { fontSize: 9, fontWeight: '800', letterSpacing: 0.4 },
  cpItemName:  { color: Colors.white, fontSize: 13, fontWeight: '700' },
  cpItemMeta:  { color: Colors.gray400, fontSize: 11, marginTop: 2 },
  cpItemNote:  { color: Colors.gray600, fontSize: 11, fontStyle: 'italic', marginTop: 2 },
  cpBodyText:  { color: Colors.gray400, fontSize: 13, lineHeight: 21 },
  cpApprovedAt:{ color: Colors.gray600, fontSize: 11, textAlign: 'center', marginTop: Spacing.xs },

  medCard:      { gap: Spacing.sm },
  medHeader:    { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  medName:      { color: Colors.white, fontSize: 14, fontWeight: '800', flex: 1 },
  medChips:     { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs },
  doseChip:     { backgroundColor: `${Colors.teal}18`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  doseChipText: { color: Colors.teal, fontSize: 12, fontWeight: '600' },
  routeChip:    { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  routeChipText:{ fontSize: 12, fontWeight: '700' },
  medNoteBox:   { backgroundColor: `${Colors.gray600}14`, borderRadius: Radius.sm, padding: Spacing.sm },
  medNoteText:  { color: Colors.gray400, fontSize: 11, lineHeight: 17, fontStyle: 'italic' },

  infoCard:     { borderLeftWidth: 4, gap: Spacing.xs },

  // Care plan not-yet-created state
  noPlanCard:   { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xl, borderColor: Colors.glassBorder },
  noPlanTitle:  { color: Colors.white, fontSize: 14, fontWeight: '700' },
  noPlanBody:   { color: Colors.gray400, fontSize: 12, textAlign: 'center', lineHeight: 19, paddingHorizontal: Spacing.md },
});

// ─────────────────────────────────────────────────────────────────────────────
// DOCTOR VIEW STYLES  (prefix: ds.)
// ─────────────────────────────────────────────────────────────────────────────
const ds = StyleSheet.create({
  header:           { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn:          { width: 40, height: 40, justifyContent: 'center' },
  headerTitle:      { color: Colors.white, fontSize: 16, fontWeight: '700', flex: 1, marginHorizontal: Spacing.sm },
  editToggleBtn:    { flexDirection: 'row', alignItems: 'center', gap: 5, paddingHorizontal: 12, paddingVertical: 6, borderRadius: Radius.full, borderWidth: 1.5, borderColor: Colors.teal },
  editToggleBtnActive: { backgroundColor: Colors.teal },
  editToggleText:   { color: Colors.teal, fontSize: 12, fontWeight: '700' },
  editedBadge:      { backgroundColor: `${Colors.amber}20`, borderWidth: 1, borderColor: `${Colors.amber}55`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3 },
  editedBadgeText:  { color: Colors.amber, fontSize: 9, fontWeight: '800' },
  editBanner:       { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, backgroundColor: `${Colors.amber}14`, borderBottomWidth: 1, borderBottomColor: `${Colors.amber}33`, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm },
  editBannerText:   { color: Colors.amber, fontSize: 12, flex: 1 },
  scroll:           { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  editableCard:     { borderColor: `${Colors.amber}44`, borderWidth: 1.5 },

  patientRow:       { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.md },
  patientAvatar:    { width: 52, height: 52, borderRadius: 26, backgroundColor: `rgba(0,194,168,0.15)`, borderWidth: 1, borderColor: `${Colors.teal}30`, alignItems: 'center', justifyContent: 'center' },
  patientInitials:  { color: Colors.teal, fontWeight: '900', fontSize: 18 },
  patientName:      { color: Colors.white, fontSize: 16, fontWeight: '800' },
  patientMeta:      { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  patientSubId:     { color: Colors.gray600, fontSize: 11, marginTop: 2, marginBottom: 4 },
  pathwayLabel:     { color: Colors.gray400, fontSize: 13 },
  sepsisAlert:      { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  sepsisText:       { color: Colors.red, fontSize: 12, fontWeight: '700' },
  conditionsRow:    { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.xs, marginTop: Spacing.sm, paddingTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.glassBorder },
  conditionChip:    { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.red}12`, borderWidth: 1, borderColor: `${Colors.red}33`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  conditionDot:     { width: 5, height: 5, borderRadius: 2.5, backgroundColor: Colors.red },
  conditionChipText:{ color: Colors.red, fontSize: 11, fontWeight: '600' },

  cardHeader:    { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: Spacing.sm, flexWrap: 'wrap' },
  cardTitle:     { color: Colors.white, fontSize: 14, fontWeight: '700', flex: 1 },
  quoteText:     { color: Colors.gray400, fontSize: 13, lineHeight: 21 },
  fieldLabel:    { color: Colors.gray400, fontSize: 11, fontWeight: '600', letterSpacing: 0.3 },

  soapEditBtn:       { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.full, borderWidth: 1.5, borderColor: Colors.teal },
  soapEditBtnActive: { backgroundColor: Colors.teal },
  soapEditBtnText:   { color: Colors.teal, fontSize: 11, fontWeight: '700' },
  soapSection:       { borderLeftWidth: 3, paddingLeft: Spacing.sm, marginTop: Spacing.sm, gap: 6 },
  soapSectionHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginBottom: 4 },
  soapBadge:         { width: 28, height: 28, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  soapBadgeLetter:   { color: Colors.navy, fontSize: 14, fontWeight: '900' },
  soapSectionTitle:  { fontSize: 13, fontWeight: '800' },
  soapSectionSub:    { color: Colors.gray600, fontSize: 10 },
  soapText:          { color: Colors.gray400, fontSize: 13, lineHeight: 21 },
  soapTextInput:     { color: Colors.white, fontSize: 13, lineHeight: 20, minHeight: 80, backgroundColor: '#112240', borderRadius: Radius.sm, padding: Spacing.sm, borderWidth: 1, borderColor: `${Colors.amber}44`, textAlignVertical: 'top' },

  codeGroupLabel: { color: Colors.gray600, fontSize: 9, fontWeight: '800', letterSpacing: 1, marginBottom: 5 },
  codeRow:        { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, borderWidth: 1, borderRadius: Radius.sm, padding: Spacing.sm, marginBottom: 5 },
  codeBadge:      { borderRadius: 6, paddingHorizontal: 5, paddingVertical: 3, alignItems: 'center', minWidth: 46 },
  codeTiny:       { fontSize: 8, fontWeight: '800', letterSpacing: 0.5 },
  codeNum:        { fontSize: 12, fontWeight: '900' },
  codeDesc:       { color: Colors.gray400, fontSize: 12, lineHeight: 17, flex: 1 },

  specialistName:   { color: Colors.white, fontSize: 15, fontWeight: '800' },
  specialistDept:   { color: Colors.blue, fontSize: 12, fontWeight: '600', marginBottom: Spacing.xs },
  dispositionText:  { color: Colors.amber, fontSize: 12, fontWeight: '700', marginTop: 4 },

  inlineInput:    { color: Colors.white, fontSize: 13, backgroundColor: '#112240', borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: 6, borderWidth: 1, borderColor: `${Colors.amber}44` },
  editListRow:    { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.xs },
  listItemText:   { fontSize: 13, lineHeight: 20, flex: 1 },
  removeBtn:      { padding: 2, marginTop: 2 },
  addBtn:         { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6 },
  addBtnText:     { color: Colors.teal, fontSize: 13, fontWeight: '600' },

  reviewCard:        { gap: Spacing.sm },
  editSummaryBanner: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, backgroundColor: `${Colors.amber}12`, borderWidth: 1, borderColor: `${Colors.amber}33`, borderRadius: Radius.sm, padding: Spacing.sm },
  editSummaryText:   { color: Colors.amber, fontSize: 12, flex: 1 },
  overrideLabel:     { color: Colors.gray400, fontSize: 12, fontWeight: '600', letterSpacing: 0.5 },
  overrideChips:     { flexDirection: 'row', gap: Spacing.xs },
  overrideChip:      { flex: 1, alignItems: 'center', paddingVertical: Spacing.xs + 2, backgroundColor: '#112240', borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm },
  overrideChipActive:{ backgroundColor: `rgba(0,194,168,0.15)`, borderColor: Colors.teal },
  overrideChipText:  { color: Colors.gray400, fontSize: 12, fontWeight: '700' },
  noteInput:         { backgroundColor: '#112240', borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.md, padding: Spacing.sm, color: Colors.white, fontSize: 14, minHeight: 80 },
  auditNote:         { color: Colors.gray600, fontSize: 11, lineHeight: 16 },

  approvedContainer: { flex: 1, padding: Spacing.xl, alignItems: 'center', justifyContent: 'center', gap: Spacing.lg },
  approvedTitle:     { color: Colors.white, fontSize: 22, fontWeight: '800', textAlign: 'center' },
  approvedText:      { color: Colors.gray400, textAlign: 'center', lineHeight: 22, fontSize: 14 },

  // Step 2 — care plan prompt
  step2Banner:   { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.md, backgroundColor: `${Colors.amber}12`, borderWidth: 1, borderColor: `${Colors.amber}33`, borderRadius: Radius.lg, padding: Spacing.md, width: '100%' },
  step2IconWrap: { width: 36, height: 36, borderRadius: 18, backgroundColor: `${Colors.amber}20`, alignItems: 'center', justifyContent: 'center' },
  step2Title:    { color: Colors.amber, fontSize: 14, fontWeight: '800' },
  step2Sub:      { color: Colors.gray400, fontSize: 12, lineHeight: 18 },
  laterBtn:      { paddingVertical: Spacing.sm },
  laterBtnText:  { color: Colors.gray600, fontSize: 13, fontWeight: '600', textDecorationLine: 'underline' },
});
