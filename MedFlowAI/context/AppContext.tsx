import React, { createContext, useContext, useState, ReactNode } from 'react';
import { TriageResult } from '../services/api';

export interface PatientProfile {
  patient_id: string;
  name: string;
  initials: string;
  dob: string;
  age: number | null;
  gender: string;
  conditions: { name: string; flag: string; is_active: boolean }[];
  visits: { encounter_id: string; date: string; symptoms: string; temp?: number; heart_rate?: number }[];
}

interface AppState {
  patientId: string;
  setPatientId: (id: string) => void;
  role: 'patient' | 'clinician';
  setRole: (r: 'patient' | 'clinician') => void;
  triageResult: TriageResult | null;
  setTriageResult: (r: TriageResult | null) => void;
  clinicianId: string;
  setClinicianId: (id: string) => void;
  isDoctor: boolean;
  profile: PatientProfile | null;
  setProfile: (p: PatientProfile | null) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [patientId, setPatientId] = useState('P00001');
  const [role, setRole] = useState<'patient' | 'clinician'>('patient');
  const [triageResult, setTriageResult] = useState<TriageResult | null>(null);
  const [clinicianId, setClinicianId] = useState('CLINICIAN_001');
  const [profile, setProfile] = useState<PatientProfile | null>(null);

  const isDoctor = clinicianId.startsWith('DR');

  return (
    <AppContext.Provider value={{
      patientId, setPatientId,
      role, setRole,
      triageResult, setTriageResult,
      clinicianId, setClinicianId,
      isDoctor,
      profile, setProfile,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside AppProvider');
  return ctx;
}
