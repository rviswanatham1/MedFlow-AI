import { API_BASE_URL } from '../constants/config';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export interface AssessPayload {
  patient_id: string;
  symptoms: string;
  duration?: string;
  pain_level?: number;
  tags?: string[];
  age?: number;
  gender?: string;
  provider?: string;
  api_key?: string;
}

export interface TriageResult {
  patient_id: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  summary: string;
  care_pathway: string;
  estimated_wait: number;
  queue_position: number;
  differentials: { condition: string; likelihood: number }[];
  recommendations: string[];
  specialist_assignment?: {
    primary_specialist: string;
    department: string;
    reason: string;
    secondary_specialist?: string;
    urgency_for_specialist: string;
    handoff_instructions: string;
    estimated_disposition: string;
  };
  telehealth_eligible?: boolean;
  // clinician-only fields
  triage_decision?: string;
  clinical_reasoning?: string;
  safety_flags?: string[];
  labs_ordered?: string[];
  imaging?: string[];
  sepsis_concern?: boolean;
}

export interface QueueEntry {
  patient_id: string;
  position: number;
  wait: number;
  urgency: string;
  pathway: string;
  status: string;
  summary?: string;
  confidence?: number;
  flag?: string | null;
  age?: number;
  gender?: string;
}

export interface AnalyticsSummary {
  active_patients: number;
  avg_wait: number;
  pending_review: number;
  escalations: number;
  forecast?: string;
}

export interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface ICD10Code {
  code: string;
  description: string;
  type: 'primary' | 'secondary';
}

export interface CPTCode {
  code: string;
  description: string;
  category: 'evaluation' | 'lab' | 'imaging' | 'procedure';
}

export interface LabOrder {
  name: string;
  urgency: 'STAT' | 'ASAP' | 'Routine';
  timing: string;
  notes?: string;
}

export interface Medication {
  name: string;
  dose: string;
  frequency: string;
  route: string;
  duration?: string;
  notes?: string;
}

export interface CarePlan {
  exists: boolean;
  patient_id?: string;
  doctor_id?: string;
  labs?: LabOrder[];
  medications?: Medication[];
  instructions?: string;
  follow_up?: string;
  diet?: string;
  activity?: string;
  approved_at?: string;
  shared_with_staff?: boolean;
  shared_with_patient?: boolean;
}

export interface ApprovedReport {
  approved: boolean;
  message?: string;
  patient_id?: string;
  approved_at?: string;
  approved_by?: string;
  audit_id?: string;
  final_urgency?: string;
  clinician_note?: string;
  summary?: string;
  care_pathway?: string;
  confidence?: number;
  differentials?: { condition: string; likelihood: number }[];
  recommendations?: string[];
  specialist_assignment?: {
    primary_specialist: string;
    department: string;
    reason: string;
    urgency_for_specialist: string;
    handoff_instructions: string;
    estimated_disposition: string;
    secondary_specialist?: string;
  } | null;
  sepsis_concern?: boolean;
  clinical_impression?: string;
  labs_and_orders?: string[];
  estimated_wait?: number;
  queue_position?: number;
  completed_at?: string;
  soap_note?: SOAPNote;
  icd10_codes?: ICD10Code[];
  cpt_codes?: CPTCode[];
  care_plan?: CarePlan;
}

export interface LoginResponse {
  success: boolean;
  role: 'patient' | 'staff';
  patient_id: string;
  name: string;
  dob?: string;
  gender?: string;
}

export const api = {
  /** Authenticate patient or staff against dataset */
  login: (patientId: string, password: string, role: 'patient' | 'staff'): Promise<LoginResponse> =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, password, role }),
    }),

  /** Run the full triage pipeline for a patient */
  assessTriage: async (payload: AssessPayload): Promise<TriageResult> => {
    const raw = await request<any>('/api/triage/assess', { method: 'POST', body: JSON.stringify(payload) });
    // API wraps in { patient_view, clinician_view } — flatten for patient use
    const pv = raw.patient_view ?? raw;
    return {
      patient_id:          pv.patient_id,
      urgency:             pv.urgency,
      confidence:          pv.confidence,
      summary:             pv.summary,
      care_pathway:        pv.care_pathway,
      estimated_wait:      pv.estimated_wait ?? pv.wait ?? 0,
      queue_position:      pv.queue_position ?? pv.position ?? 1,
      differentials:       pv.differentials ?? [],
      recommendations:     pv.recommendations ?? [],
      specialist_assignment: pv.specialist_assignment ?? pv.specialist ?? undefined,
      telehealth_eligible: pv.telehealth_eligible,
      // clinician fields
      triage_decision:     raw.clinician_view?.triage_decision,
      clinical_reasoning:  raw.clinician_view?.clinical_reasoning,
      safety_flags:        raw.clinician_view?.safety_flags,
      labs_ordered:        raw.clinician_view?.labs_ordered,
      imaging:             raw.clinician_view?.imaging,
      sepsis_concern:      raw.clinician_view?.sepsis_concern ?? pv.sepsis_alert,
    };
  },

  /** Get the patient-facing view of a triage result */
  getPatientTriage: async (patientId: string): Promise<TriageResult> => {
    const raw = await request<any>(`/api/triage/${patientId}?role=patient`);
    const pv = raw.patient_view ?? raw;
    return {
      patient_id: pv.patient_id, urgency: pv.urgency, confidence: pv.confidence,
      summary: pv.summary, care_pathway: pv.care_pathway, estimated_wait: pv.estimated_wait,
      queue_position: pv.queue_position ?? pv.position ?? 1, differentials: pv.differentials ?? [],
      recommendations: pv.recommendations ?? [],
      specialist_assignment: pv.specialist_assignment ?? pv.specialist,
      telehealth_eligible: pv.telehealth_eligible,
    };
  },

  /** Get the clinician view of a triage result */
  getClinicianTriage: async (patientId: string): Promise<TriageResult & { diagnostics?: any }> => {
    const raw = await request<any>(`/api/triage/${patientId}?role=clinician`);
    const pv = raw.patient_view ?? raw;
    const cv = raw.clinician_view ?? raw;
    return {
      patient_id: pv.patient_id ?? cv.patient_id, urgency: pv.urgency, confidence: pv.confidence,
      summary: pv.summary, care_pathway: pv.care_pathway ?? cv.patient_assignment,
      estimated_wait: pv.estimated_wait, queue_position: pv.queue_position,
      differentials: pv.differentials ?? [], recommendations: pv.recommendations ?? [],
      specialist_assignment: pv.specialist ?? pv.specialist_assignment,
      telehealth_eligible: pv.telehealth_eligible,
      triage_decision: cv.triage_decision, clinical_reasoning: cv.clinical_reasoning,
      safety_flags: cv.safety_flags, labs_ordered: cv.labs_ordered, imaging: cv.imaging,
      sepsis_concern: cv.sepsis_concern ?? pv.sepsis_alert,
      // Pass diagnostics sub-object so staff screen can access soap_note/icd10_codes/cpt_codes
      diagnostics: cv.diagnostics ?? undefined,
    };
  },

  /** Clinician approves / overrides AI recommendation with optional edits */
  approveTriage: (
    patientId: string,
    clinicianId: string,
    note?: string,
    urgencyOverride?: string,
    edits?: {
      summary?: string;
      clinical_impression?: string;
      differentials?: { condition: string; likelihood: number }[];
      recommendations?: string[];
      labs_and_orders?: string[];
      specialist_primary?: string;
      specialist_department?: string;
      specialist_reason?: string;
      specialist_urgency?: string;
      specialist_handoff?: string;
      specialist_disposition?: string;
    },
  ) =>
    request('/api/triage/approve', {
      method: 'POST',
      body: JSON.stringify({
        patient_id:       patientId,
        clinician_id:     clinicianId,
        note,
        urgency_override: urgencyOverride,
        edits,
      }),
    }),

  /** Full real-time queue list (clinician) */
  getQueue: async (): Promise<QueueEntry[]> => {
    const data = await request<any>('/api/queue');
    // Backend returns { queue: [...], summary: {...} }
    const items: any[] = data.queue ?? data ?? [];
    // Normalise "id" → "patient_id" sent by the backend
    return items.map((e: any) => ({
      patient_id:  e.patient_id ?? e.id ?? '',
      position:    e.queue_position ?? e.position ?? 0,
      wait:        e.wait ?? e.estimated_wait ?? 0,
      urgency:     e.urgency ?? 'medium',
      pathway:     e.pathway ?? e.care_pathway ?? '',
      status:      e.status ?? 'pending_review',
      summary:     e.summary ?? '',
      confidence:  e.confidence,
      flag:        e.flag ?? null,
      age:         e.age,
      gender:      e.gender,
    }));
  },

  /** Patient's queue position and wait */
  getQueueStatus: (patientId: string): Promise<{ position: number; wait: number; urgency: string }> =>
    request(`/api/queue/status?patient_id=${patientId}`),

  /** Appointment slots / plan for a patient */
  getAppointments: (patientId: string): Promise<any[]> =>
    request(`/api/appointments?patient_id=${patientId}`),

  /** Book an appointment */
  bookAppointment: (patientId: string, slot: any) =>
    request('/api/appointments/book', { method: 'POST', body: JSON.stringify({ patient_id: patientId, ...slot }) }),

  /** Specialist referral for patient */
  getReferrals: (patientId: string): Promise<any> =>
    request(`/api/referrals?patient_id=${patientId}`),

  /** High-level dashboard metrics */
  getAnalyticsSummary: (): Promise<AnalyticsSummary> => request('/api/analytics/summary'),

  /** Detailed performance metrics */
  getAnalyticsPerformance: (): Promise<any> => request('/api/analytics/performance'),

  /** AI operational forecast */
  getAnalyticsForecast: (): Promise<any> => request('/api/analytics/forecast'),

  /** Full patient profile — demographics, conditions, visit history */
  getPatientProfile: (patientId: string): Promise<{
    patient_id: string; name: string; initials: string;
    dob: string; age: number | null; gender: string;
    conditions: { name: string; flag: string; is_active: boolean }[];
    visits: { encounter_id: string; date: string; symptoms: string; temp?: number; heart_rate?: number }[];
  }> => request(`/api/patients/profile?patient_id=${patientId}`),

  /** Approved clinical report — only populated after clinician approves */
  getApprovedReport: (patientId: string): Promise<ApprovedReport> =>
    request(`/api/triage/${patientId}/report`),

  /** Patient search */
  searchPatients: (query: string, field: 'name' | 'mrn' = 'name'): Promise<{
    patient_id: string; name: string; dob: string; gender: string; insurance: string; last_triage?: string;
  }[]> =>
    request<{ results: any[] }>(`/api/patients/search?q=${encodeURIComponent(query)}&field=${field}`)
      .then(r => r.results ?? []),

  /** Single patient record */
  getPatient: (patientId: string): Promise<any> => request(`/api/patients/${patientId}`),

  /** Staff worklist */
  getWorklist: (): Promise<any[]> => request('/api/staff/worklist'),

  /** Save (create or update) a doctor's care plan for a patient */
  saveCarePlan: (plan: { patient_id: string; doctor_id: string; labs: LabOrder[]; medications: Medication[]; instructions: string; follow_up: string; diet?: string; activity?: string }) =>
    request('/api/triage/care-plan', { method: 'POST', body: JSON.stringify(plan) }),

  /** Get care plan for a patient — role=patient gates behind explicit doctor creation */
  getCarePlan: (patientId: string, role: 'patient' | 'staff' | 'doctor' = 'staff'): Promise<CarePlan> =>
    request(`/api/triage/${patientId}/care-plan?role=${role}`),

  /** Patients whose diagnosis is approved but care plan not yet created (doctor dashboard) */
  getPendingCarePlans: (): Promise<{ patient_id: string; approved_at: string; approved_by: string; urgency: string; summary: string; pathway: string }[]> =>
    request('/api/staff/pending-care-plans'),
};
