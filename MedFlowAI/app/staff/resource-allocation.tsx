import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Divider } from '../../components/ui';

// TODO: GET  /api/resources/rooms           → live room/bay status
// TODO: POST /api/resources/assign          → assign patient to room
// TODO: GET  /api/resources/staff/available → available clinicians + nurses per shift
// TODO: POST /api/resources/staff/assign    → assign staff member to patient/room
// TODO: GET  /api/resources/equipment       → equipment availability
// AI Scheduling & Disposition Agent feeds recommendations here

type RoomStatus = 'available' | 'occupied' | 'cleaning' | 'reserved';
type RoomType   = 'exam' | 'trauma' | 'observation' | 'procedure' | 'triage';

interface Room {
  id: string;
  name: string;
  type: RoomType;
  status: RoomStatus;
  patient?: string;
  mrn?: string;
  since?: string;
  assignedTo?: string;
  urgency?: 'low' | 'medium' | 'high' | 'critical';
  aiRecommended?: boolean;
}

interface StaffMember {
  id: string;
  name: string;
  role: string;
  status: 'available' | 'busy' | 'on_break';
  currentPatient?: string;
  load: number; // 0-100
}

const ROOMS: Room[] = [
  { id: 'r1',  name: 'Bay 1',       type: 'trauma',      status: 'occupied',   patient: 'Marcus K.',  mrn: 'MRN-006739', since: '09:12 AM', assignedTo: 'Dr. Malik',   urgency: 'critical' },
  { id: 'r2',  name: 'Bay 2',       type: 'exam',        status: 'occupied',   patient: 'Jordan D.',  mrn: 'MRN-004221', since: '10:34 AM', assignedTo: 'Dr. Patel',   urgency: 'medium'   },
  { id: 'r3',  name: 'Bay 3',       type: 'exam',        status: 'available',  aiRecommended: true  },
  { id: 'r4',  name: 'Bay 4',       type: 'exam',        status: 'cleaning'   },
  { id: 'r5',  name: 'Bay 5',       type: 'observation', status: 'occupied',   patient: 'Sarah J.',   mrn: 'MRN-003345', since: '11:20 AM', assignedTo: 'Nurse Kim',   urgency: 'low'      },
  { id: 'r6',  name: 'Bay 6',       type: 'observation', status: 'available'  },
  { id: 'r7',  name: 'Triage 1',    type: 'triage',      status: 'occupied',   patient: 'Rosa B.',    mrn: 'MRN-002184', since: '10:55 AM', assignedTo: 'Nurse Lee',   urgency: 'medium'   },
  { id: 'r8',  name: 'Triage 2',    type: 'triage',      status: 'available'  },
  { id: 'r9',  name: 'Procedure 1', type: 'procedure',   status: 'reserved',  assignedTo: 'Dr. Chen' },
  { id: 'r10', name: 'Procedure 2', type: 'procedure',   status: 'available'  },
];

const STAFF: StaffMember[] = [
  { id: 's1', name: 'Dr. Ayesha Malik', role: 'Attending MD',   status: 'busy',      currentPatient: 'Marcus K.', load: 90 },
  { id: 's2', name: 'Dr. Priya Patel',  role: 'Attending MD',   status: 'busy',      currentPatient: 'Jordan D.', load: 70 },
  { id: 's3', name: 'Dr. Marcus Webb',  role: 'Attending MD',   status: 'available', load: 30 },
  { id: 's4', name: 'Dr. Sarah Chen',   role: 'Cardiologist',   status: 'busy',      load: 80 },
  { id: 's5', name: 'Nurse Kim',        role: 'RN',             status: 'busy',      currentPatient: 'Sarah J.',  load: 75 },
  { id: 's6', name: 'Nurse Lee',        role: 'RN',             status: 'busy',      currentPatient: 'Rosa B.',   load: 60 },
  { id: 's7', name: 'Nurse Torres',     role: 'RN',             status: 'available', load: 20 },
  { id: 's8', name: 'Nurse Park',       role: 'Charge Nurse',   status: 'on_break',  load: 0  },
];

const ROOM_STATUS_CFG: Record<RoomStatus, { color: string; label: string; bg: string }> = {
  available: { color: Colors.green, label: 'Available', bg: `${Colors.green}18` },
  occupied:  { color: Colors.red,   label: 'Occupied',  bg: `${Colors.red}12`   },
  cleaning:  { color: Colors.amber, label: 'Cleaning',  bg: `${Colors.amber}15` },
  reserved:  { color: Colors.blue,  label: 'Reserved',  bg: `${Colors.blue}15`  },
};

const URGENCY_CFG = {
  low:      Colors.green,
  medium:   Colors.amber,
  high:     Colors.red,
  critical: Colors.urgencyCritical,
};

const STAFF_STATUS_CFG = {
  available: { color: Colors.green, label: 'Available' },
  busy:      { color: Colors.amber, label: 'Busy'      },
  on_break:  { color: Colors.gray400,label: 'Break'    },
};

type View2 = 'rooms' | 'staff';

export default function ResourceAllocationScreen() {
  const router = useRouter();
  const [view, setView] = useState<View2>('rooms');
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);

  const availableRooms = ROOMS.filter(r => r.status === 'available').length;
  const occupiedRooms  = ROOMS.filter(r => r.status === 'occupied').length;
  const availableStaff = STAFF.filter(s => s.status === 'available').length;

  const urgencyColor = (u?: string) => u ? (URGENCY_CFG as any)[u] ?? Colors.gray400 : Colors.gray400;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Resource Allocation</Text>
        <View style={styles.liveChip}>
          <View style={styles.liveDot} />
          <Text style={styles.liveText}>LIVE</Text>
        </View>
      </View>

      {/* Summary strip */}
      <View style={styles.summaryStrip}>
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.green }]}>{availableRooms}</Text>
          <Text style={styles.summaryLabel}>Rooms Free</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.red }]}>{occupiedRooms}</Text>
          <Text style={styles.summaryLabel}>Occupied</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.green }]}>{availableStaff}</Text>
          <Text style={styles.summaryLabel}>Staff Free</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.teal }]}>{STAFF.length}</Text>
          <Text style={styles.summaryLabel}>Total Staff</Text>
        </View>
      </View>

      {/* View toggle */}
      <View style={styles.toggle}>
        <TouchableOpacity
          style={[styles.toggleBtn, view === 'rooms' && styles.toggleBtnActive]}
          onPress={() => setView('rooms')}
        >
          <MaterialCommunityIcons name="floor-plan" size={15} color={view === 'rooms' ? Colors.navy : Colors.gray400} />
          <Text style={[styles.toggleText, view === 'rooms' && styles.toggleTextActive]}>Rooms & Bays</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, view === 'staff' && styles.toggleBtnActive]}
          onPress={() => setView('staff')}
        >
          <MaterialCommunityIcons name="account-group-outline" size={15} color={view === 'staff' ? Colors.navy : Colors.gray400} />
          <Text style={[styles.toggleText, view === 'staff' && styles.toggleTextActive]}>Staff</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {/* AI recommendation banner */}
        <View style={styles.aiRec}>
          <MaterialCommunityIcons name="chip" size={16} color={Colors.teal} />
          <View style={{ flex: 1 }}>
            <Text style={styles.aiRecTitle}>AI Recommendation</Text>
            <Text style={styles.aiRecText}>
              Bay 3 is flagged as optimal for next Urgent Care intake. Dr. Webb available and load is low.
            </Text>
          </View>
        </View>

        {/* ROOMS VIEW */}
        {view === 'rooms' && (
          <>
            {/* Room grid */}
            <View style={styles.roomGrid}>
              {ROOMS.map(room => {
                const sc = ROOM_STATUS_CFG[room.status];
                const isSelected = selectedRoom === room.id;
                return (
                  <TouchableOpacity
                    key={room.id}
                    style={[
                      styles.roomCell,
                      { backgroundColor: sc.bg, borderColor: `${sc.color}55` },
                      room.aiRecommended && styles.roomCellAI,
                      isSelected && styles.roomCellSelected,
                    ]}
                    onPress={() => setSelectedRoom(isSelected ? null : room.id)}
                  >
                    {room.aiRecommended && (
                      <View style={styles.aiPin}>
                        <MaterialCommunityIcons name="chip" size={9} color={Colors.teal} />
                      </View>
                    )}
                    <Text style={styles.roomName}>{room.name}</Text>
                    <View style={[styles.roomStatusDot, { backgroundColor: sc.color }]} />
                    {room.patient && (
                      <Text style={styles.roomPatient} numberOfLines={1}>{room.patient.split(' ')[0]}</Text>
                    )}
                    {room.urgency && (
                      <View style={[styles.urgencyStripe, { backgroundColor: urgencyColor(room.urgency) }]} />
                    )}
                    <Text style={[styles.roomStatusLabel, { color: sc.color }]}>{sc.label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Selected room detail */}
            {selectedRoom && (() => {
              const room = ROOMS.find(r => r.id === selectedRoom)!;
              const sc = ROOM_STATUS_CFG[room.status];
              return (
                <GlassCard style={styles.roomDetail}>
                  <View style={styles.roomDetailHeader}>
                    <Text style={styles.roomDetailName}>{room.name}</Text>
                    <View style={[styles.statusBadge, { backgroundColor: sc.bg, borderColor: `${sc.color}44` }]}>
                      <Text style={[styles.statusBadgeText, { color: sc.color }]}>{sc.label}</Text>
                    </View>
                  </View>
                  <View style={styles.roomDetailMeta}>
                    <Text style={styles.metaLabel}>Type</Text>
                    <Text style={styles.metaVal}>{room.type.charAt(0).toUpperCase() + room.type.slice(1)}</Text>
                  </View>
                  {room.patient && (
                    <>
                      <View style={styles.roomDetailMeta}>
                        <Text style={styles.metaLabel}>Patient</Text>
                        <Text style={styles.metaVal}>{room.patient} · {room.mrn}</Text>
                      </View>
                      <View style={styles.roomDetailMeta}>
                        <Text style={styles.metaLabel}>Since</Text>
                        <Text style={styles.metaVal}>{room.since}</Text>
                      </View>
                      <View style={styles.roomDetailMeta}>
                        <Text style={styles.metaLabel}>Assigned to</Text>
                        <Text style={styles.metaVal}>{room.assignedTo}</Text>
                      </View>
                    </>
                  )}
                  {room.status === 'available' && (
                    <View style={styles.roomDetailActions}>
                      <TouchableOpacity style={styles.assignBtn}>
                        <MaterialCommunityIcons name="account-plus-outline" size={15} color={Colors.navy} />
                        <Text style={styles.assignBtnText}>Assign Patient</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.reserveBtn}>
                        <Text style={styles.reserveBtnText}>Reserve</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                  {room.status === 'occupied' && (
                    <View style={styles.roomDetailActions}>
                      <TouchableOpacity style={styles.dischargeBtn}>
                        <MaterialCommunityIcons name="home-outline" size={15} color={Colors.white} />
                        <Text style={styles.dischargeBtnText}>Discharge</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.transferBtn}>
                        <Text style={styles.transferBtnText}>Transfer</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </GlassCard>
              );
            })()}
          </>
        )}

        {/* STAFF VIEW */}
        {view === 'staff' && (
          <View style={styles.staffList}>
            {STAFF.map(s => {
              const sc = STAFF_STATUS_CFG[s.status];
              const loadColor = s.load >= 80 ? Colors.red : s.load >= 50 ? Colors.amber : Colors.green;
              return (
                <GlassCard key={s.id} style={styles.staffCard}>
                  <View style={styles.staffHeader}>
                    <View style={styles.staffAvatar}>
                      <Text style={styles.staffAvatarText}>
                        {s.name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                      </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.staffName}>{s.name}</Text>
                      <Text style={styles.staffRole}>{s.role}</Text>
                      {s.currentPatient && (
                        <Text style={styles.staffPatient}>With: {s.currentPatient}</Text>
                      )}
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: `${sc.color}18`, borderColor: `${sc.color}44` }]}>
                      <Text style={[styles.statusBadgeText, { color: sc.color }]}>{sc.label}</Text>
                    </View>
                  </View>
                  <View style={styles.loadRow}>
                    <Text style={styles.loadLabel}>Load</Text>
                    <View style={styles.loadTrack}>
                      <View style={[styles.loadFill, { width: `${s.load}%` as any, backgroundColor: loadColor }]} />
                    </View>
                    <Text style={[styles.loadPct, { color: loadColor }]}>{s.load}%</Text>
                  </View>
                  {s.status === 'available' && (
                    <TouchableOpacity style={styles.assignStaffBtn}>
                      <MaterialCommunityIcons name="account-arrow-right-outline" size={14} color={Colors.teal} />
                      <Text style={styles.assignStaffText}>Assign to Patient</Text>
                    </TouchableOpacity>
                  )}
                </GlassCard>
              );
            })}
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  liveChip: { flexDirection: 'row', alignItems: 'center', gap: 5, backgroundColor: `${Colors.red}18`, borderWidth: 1, borderColor: `${Colors.red}44`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.red },
  liveText: { color: Colors.red, fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  summaryStrip: { flexDirection: 'row', backgroundColor: Colors.navyMid, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder, paddingVertical: Spacing.sm },
  summaryStat: { flex: 1, alignItems: 'center', gap: 2 },
  summaryVal: { fontSize: 22, fontWeight: '900' },
  summaryLabel: { color: Colors.gray600, fontSize: 9, fontWeight: '600' },
  summaryDivider: { width: 1, backgroundColor: Colors.glassBorder, marginVertical: 4 },
  toggle: { flexDirection: 'row', backgroundColor: Colors.navyMid, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder, padding: 6, gap: 6 },
  toggleBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: Spacing.sm, borderRadius: Radius.sm },
  toggleBtnActive: { backgroundColor: Colors.teal },
  toggleText: { color: Colors.gray400, fontSize: 13, fontWeight: '600' },
  toggleTextActive: { color: Colors.navy },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  aiRec: { flexDirection: 'row', gap: Spacing.sm, alignItems: 'flex-start', backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}30`, borderRadius: Radius.md, padding: Spacing.md },
  aiRecTitle: { color: Colors.teal, fontSize: 13, fontWeight: '700', marginBottom: 2 },
  aiRecText: { color: Colors.gray400, fontSize: 12, lineHeight: 17 },
  roomGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  roomCell: { width: '30.5%', aspectRatio: 1, borderRadius: Radius.md, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center', gap: 4, position: 'relative', overflow: 'hidden' },
  roomCellAI: { borderColor: `${Colors.teal}88`, borderWidth: 2 },
  roomCellSelected: { transform: [{ scale: 1.04 }] },
  aiPin: { position: 'absolute', top: 5, right: 5, backgroundColor: Colors.tealDim, borderRadius: 99, padding: 2 },
  roomName: { color: Colors.white, fontSize: 12, fontWeight: '700', textAlign: 'center' },
  roomStatusDot: { width: 7, height: 7, borderRadius: 3.5 },
  roomPatient: { color: Colors.gray400, fontSize: 10, textAlign: 'center', maxWidth: 70 },
  urgencyStripe: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 3 },
  roomStatusLabel: { fontSize: 9, fontWeight: '700', letterSpacing: 0.3 },
  roomDetail: { gap: Spacing.sm },
  roomDetailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  roomDetailName: { color: Colors.white, fontSize: 17, fontWeight: '800' },
  statusBadge: { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 3 },
  statusBadgeText: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },
  roomDetailMeta: { flexDirection: 'row', gap: Spacing.md },
  metaLabel: { color: Colors.gray600, fontSize: 12, width: 80 },
  metaVal: { color: Colors.white, fontSize: 12, fontWeight: '600', flex: 1 },
  roomDetailActions: { flexDirection: 'row', gap: Spacing.sm, marginTop: Spacing.xs },
  assignBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, backgroundColor: Colors.teal, borderRadius: Radius.sm, paddingVertical: Spacing.sm },
  assignBtnText: { color: Colors.navy, fontWeight: '800', fontSize: 13 },
  reserveBtn: { flex: 1, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingVertical: Spacing.sm, alignItems: 'center' },
  reserveBtnText: { color: Colors.gray400, fontSize: 13, fontWeight: '600' },
  dischargeBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, backgroundColor: Colors.red, borderRadius: Radius.sm, paddingVertical: Spacing.sm },
  dischargeBtnText: { color: Colors.white, fontWeight: '800', fontSize: 13 },
  transferBtn: { flex: 1, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingVertical: Spacing.sm, alignItems: 'center' },
  transferBtnText: { color: Colors.gray400, fontSize: 13, fontWeight: '600' },
  staffList: { gap: Spacing.sm },
  staffCard: { gap: Spacing.sm },
  staffHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  staffAvatar: { width: 42, height: 42, borderRadius: 21, backgroundColor: Colors.navyLight, alignItems: 'center', justifyContent: 'center' },
  staffAvatarText: { color: Colors.teal, fontWeight: '800', fontSize: 13 },
  staffName: { color: Colors.white, fontSize: 14, fontWeight: '700' },
  staffRole: { color: Colors.gray400, fontSize: 12, marginTop: 2 },
  staffPatient: { color: Colors.teal, fontSize: 11, marginTop: 2 },
  loadRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  loadLabel: { color: Colors.gray600, fontSize: 11, width: 28 },
  loadTrack: { flex: 1, height: 6, backgroundColor: Colors.navyLight, borderRadius: Radius.full, overflow: 'hidden' },
  loadFill: { height: '100%', borderRadius: Radius.full },
  loadPct: { fontSize: 12, fontWeight: '700', width: 32, textAlign: 'right' },
  assignStaffBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start', backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}30`, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  assignStaffText: { color: Colors.teal, fontSize: 12, fontWeight: '600' },
});
