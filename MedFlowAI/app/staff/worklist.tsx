import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';
import { GlassCard, Divider } from '../../components/ui';

// TODO: GET  /api/staff/worklist?clinician_id=  → list of tasks assigned to clinician
// TODO: POST /api/staff/tasks/:id/complete      → mark task done + audit log
// TODO: POST /api/staff/tasks/:id/reassign      → reassign to another team member
// TODO: GET  /api/staff/tasks/overdue           → tasks past due time
// Connects to: EHR task module (Epic InBasket / Cerner Message Center)

type Priority = 'urgent' | 'high' | 'normal' | 'low';
type TaskStatus = 'pending' | 'in_progress' | 'done';
type TaskType = 'follow_up' | 'review' | 'order' | 'referral' | 'care_coord' | 'discharge' | 'callback';

interface Task {
  id: string;
  type: TaskType;
  title: string;
  patient: string;
  mrn: string;
  due: string;
  priority: Priority;
  status: TaskStatus;
  assignee: string;
  note?: string;
  aiGenerated: boolean;
}

const TASKS: Task[] = [
  { id: 't1', type: 'review',     title: 'Review AI triage — chest pain',       patient: 'Jordan D.',  mrn: 'MRN-004221', due: 'Now',     priority: 'urgent', status: 'pending',     assignee: 'Dr. Malik', note: 'Safety Agent flagged for clinician review',             aiGenerated: true  },
  { id: 't2', type: 'order',      title: 'Order ECG for PT-0042',               patient: 'Jordan D.',  mrn: 'MRN-004221', due: '15 min',  priority: 'urgent', status: 'pending',     assignee: 'Dr. Malik', note: 'Recommended by Clinical Reasoning Agent',               aiGenerated: true  },
  { id: 't3', type: 'review',     title: 'Escalation — stroke indicators',      patient: 'Marcus K.',  mrn: 'MRN-006739', due: 'Now',     priority: 'urgent', status: 'in_progress', assignee: 'Dr. Malik', note: 'Safety Agent: ESCALATED. Neurology consult needed.',    aiGenerated: true  },
  { id: 't4', type: 'callback',   title: 'Return call — lab results question',  patient: 'Rosa B.',    mrn: 'MRN-002184', due: '30 min',  priority: 'high',   status: 'pending',     assignee: 'Dr. Malik', note: 'Patient left voicemail re: lipid panel results',         aiGenerated: false },
  { id: 't5', type: 'referral',   title: 'Submit cardiology referral',          patient: 'Jordan D.',  mrn: 'MRN-004221', due: '1h',      priority: 'high',   status: 'pending',     assignee: 'Care Team', note: 'Auth required — BCBS. Submit via Availity.',             aiGenerated: false },
  { id: 't6', type: 'follow_up',  title: 'Post-discharge follow-up call',       patient: 'Yusuf O.',   mrn: 'MRN-009012', due: '2h',      priority: 'normal', status: 'pending',     assignee: 'Nurse Kim', note: 'Discharged this morning. Check medication adherence.',   aiGenerated: false },
  { id: 't7', type: 'care_coord', title: 'Coordinate home health services',     patient: 'Daniel M.',  mrn: 'MRN-007890', due: 'Today',   priority: 'normal', status: 'pending',     assignee: 'Care Team', note: 'High fall risk. Arrange PT evaluation.',                aiGenerated: false },
  { id: 't8', type: 'discharge',  title: 'Prepare discharge summary',           patient: 'Sarah J.',   mrn: 'MRN-003345', due: 'Today',   priority: 'normal', status: 'in_progress', assignee: 'Dr. Malik', note: null,                                                     aiGenerated: false },
  { id: 't9', type: 'order',      title: 'Renew medication — Lisinopril',       patient: 'Rosa B.',    mrn: 'MRN-002184', due: 'Tomorrow',priority: 'low',    status: 'pending',     assignee: 'Dr. Malik', note: '90-day refill request from Surescripts',                 aiGenerated: false },
];

const PRIORITY_CFG: Record<Priority, { color: string; label: string }> = {
  urgent: { color: Colors.red,    label: 'Urgent' },
  high:   { color: Colors.amber,  label: 'High'   },
  normal: { color: Colors.blue,   label: 'Normal' },
  low:    { color: Colors.gray400,label: 'Low'     },
};

const TYPE_CFG: Record<TaskType, { icon: string; color: string }> = {
  follow_up:  { icon: 'phone-outline',             color: Colors.blue  },
  review:     { icon: 'clipboard-text-outline',    color: Colors.teal  },
  order:      { icon: 'prescription',              color: Colors.amber },
  referral:   { icon: 'account-switch-outline',    color: Colors.green },
  care_coord: { icon: 'account-heart-outline',     color: Colors.teal  },
  discharge:  { icon: 'home-outline',              color: Colors.blue  },
  callback:   { icon: 'phone-return-outline',      color: Colors.amber },
};

type Filter = 'all' | 'urgent' | 'ai' | 'mine';

export default function WorklistScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>('all');
  const [tasks, setTasks] = useState<Task[]>(TASKS);

  const filtered = tasks.filter(t => {
    if (filter === 'urgent') return t.priority === 'urgent';
    if (filter === 'ai')     return t.aiGenerated;
    if (filter === 'mine')   return t.assignee === 'Dr. Malik';
    return true;
  }).filter(t => t.status !== 'done');

  const doneCount   = tasks.filter(t => t.status === 'done').length;
  const urgentCount = tasks.filter(t => t.priority === 'urgent' && t.status !== 'done').length;
  const aiCount     = tasks.filter(t => t.aiGenerated && t.status !== 'done').length;

  const markDone = (id: string) => {
    // TODO: POST /api/staff/tasks/:id/complete
    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'done' } : t));
  };

  const markInProgress = (id: string) => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, status: 'in_progress' } : t));
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Care Team Worklist</Text>
        <View style={styles.doneChip}>
          <MaterialCommunityIcons name="check-circle-outline" size={13} color={Colors.green} />
          <Text style={styles.doneText}>{doneCount} done</Text>
        </View>
      </View>

      {/* Summary strip */}
      <View style={styles.summaryStrip}>
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.red }]}>{urgentCount}</Text>
          <Text style={styles.summaryLabel}>Urgent</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.teal }]}>{aiCount}</Text>
          <Text style={styles.summaryLabel}>AI Tasks</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.white }]}>{filtered.length}</Text>
          <Text style={styles.summaryLabel}>Pending</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryStat}>
          <Text style={[styles.summaryVal, { color: Colors.green }]}>{doneCount}</Text>
          <Text style={styles.summaryLabel}>Done</Text>
        </View>
      </View>

      {/* Filters */}
      <View style={styles.filterRow}>
        {([
          { key: 'all',    label: 'All'        },
          { key: 'urgent', label: '🔴 Urgent'   },
          { key: 'ai',     label: '🤖 AI Tasks' },
          { key: 'mine',   label: 'Mine'        },
        ] as { key: Filter; label: string }[]).map(f => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterChip, filter === f.key && styles.filterChipActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[styles.filterText, filter === f.key && styles.filterTextActive]}>{f.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>

        {filtered.length === 0 && (
          <View style={styles.emptyState}>
            <MaterialCommunityIcons name="check-all" size={52} color={Colors.teal} />
            <Text style={styles.emptyTitle}>All clear!</Text>
            <Text style={styles.emptyText}>No tasks in this category</Text>
          </View>
        )}

        {filtered.map(task => {
          const pri  = PRIORITY_CFG[task.priority];
          const type = TYPE_CFG[task.type];
          const isInProgress = task.status === 'in_progress';

          return (
            <GlassCard
              key={task.id}
              style={[
                styles.taskCard,
                task.priority === 'urgent' && styles.taskCardUrgent,
                isInProgress && styles.taskCardInProgress,
              ]}
            >
              {/* Priority bar */}
              <View style={[styles.priorityBar, { backgroundColor: pri.color }]} />

              <View style={styles.taskBody}>
                {/* Header */}
                <View style={styles.taskHeader}>
                  <View style={[styles.typeIconBg, { backgroundColor: `${type.color}18` }]}>
                    <MaterialCommunityIcons name={type.icon as any} size={18} color={type.color} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.taskTitle}>{task.title}</Text>
                    <View style={styles.taskMeta}>
                      <Text style={styles.taskPatient}>{task.patient}</Text>
                      <Text style={styles.taskMrn}>{task.mrn}</Text>
                    </View>
                  </View>
                  <View style={styles.taskRight}>
                    <View style={[styles.priBadge, { backgroundColor: `${pri.color}18`, borderColor: `${pri.color}44` }]}>
                      <Text style={[styles.priText, { color: pri.color }]}>{pri.label}</Text>
                    </View>
                    <Text style={[styles.dueText, task.due === 'Now' && { color: Colors.red }]}>
                      {task.due === 'Now' ? '🔴 Now' : `Due ${task.due}`}
                    </Text>
                  </View>
                </View>

                {/* AI badge */}
                {task.aiGenerated && (
                  <View style={styles.aiBadge}>
                    <MaterialCommunityIcons name="chip" size={11} color={Colors.teal} />
                    <Text style={styles.aiText}>AI Generated</Text>
                  </View>
                )}

                {/* Note */}
                {task.note && (
                  <Text style={styles.taskNote}>{task.note}</Text>
                )}

                {/* Assignee */}
                <View style={styles.assigneeRow}>
                  <MaterialCommunityIcons name="account-outline" size={13} color={Colors.gray600} />
                  <Text style={styles.assigneeText}>{task.assignee}</Text>
                  {isInProgress && (
                    <View style={styles.inProgressChip}>
                      <View style={styles.inProgressDot} />
                      <Text style={styles.inProgressText}>In Progress</Text>
                    </View>
                  )}
                </View>

                {/* Actions */}
                <View style={styles.taskActions}>
                  <TouchableOpacity
                    style={styles.doneBtn}
                    onPress={() => markDone(task.id)}
                  >
                    <MaterialCommunityIcons name="check" size={15} color={Colors.navy} />
                    <Text style={styles.doneBtnText}>Done</Text>
                  </TouchableOpacity>

                  {!isInProgress && (
                    <TouchableOpacity
                      style={styles.startBtn}
                      onPress={() => markInProgress(task.id)}
                    >
                      <Text style={styles.startBtnText}>Start</Text>
                    </TouchableOpacity>
                  )}

                  <TouchableOpacity
                    style={styles.viewBtn}
                    onPress={() => router.push({ pathname: '/staff/patient-detail', params: { id: task.mrn } })}
                  >
                    <Text style={styles.viewBtnText}>View Patient</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </GlassCard>
          );
        })}

        {/* Done section */}
        {doneCount > 0 && (
          <View style={styles.doneSection}>
            <Text style={styles.doneSectionTitle}>Completed Today ({doneCount})</Text>
            {tasks.filter(t => t.status === 'done').map(task => (
              <View key={task.id} style={styles.doneRow}>
                <MaterialCommunityIcons name="check-circle" size={16} color={Colors.green} />
                <Text style={styles.doneRowText}>{task.title}</Text>
                <Text style={styles.doneRowPatient}>{task.patient}</Text>
              </View>
            ))}
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
  doneChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.green}18`, borderWidth: 1, borderColor: `${Colors.green}30`, borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4 },
  doneText: { color: Colors.green, fontSize: 11, fontWeight: '700' },
  summaryStrip: { flexDirection: 'row', backgroundColor: Colors.navyMid, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder, paddingVertical: Spacing.sm },
  summaryStat: { flex: 1, alignItems: 'center', gap: 2 },
  summaryVal: { fontSize: 22, fontWeight: '900' },
  summaryLabel: { color: Colors.gray600, fontSize: 10, fontWeight: '600' },
  summaryDivider: { width: 1, backgroundColor: Colors.glassBorder, marginVertical: 4 },
  filterRow: { flexDirection: 'row', gap: Spacing.xs, padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  filterChip: { flex: 1, alignItems: 'center', paddingVertical: Spacing.xs + 1, backgroundColor: Colors.navyMid, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full },
  filterChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  filterText: { color: Colors.gray400, fontSize: 11, fontWeight: '600' },
  filterTextActive: { color: Colors.teal },
  scroll: { padding: Spacing.md, gap: Spacing.sm, paddingBottom: Spacing.xxl },
  emptyState: { alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xxl },
  emptyTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  emptyText: { color: Colors.gray400, fontSize: 14 },
  taskCard: { flexDirection: 'row', padding: 0, overflow: 'hidden' },
  taskCardUrgent: { borderColor: `${Colors.red}44`, backgroundColor: `${Colors.red}05` },
  taskCardInProgress: { borderColor: `${Colors.amber}44`, backgroundColor: `${Colors.amber}05` },
  priorityBar: { width: 4, borderRadius: 0 },
  taskBody: { flex: 1, padding: Spacing.md, gap: Spacing.sm },
  taskHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  typeIconBg: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  taskTitle: { color: Colors.white, fontSize: 14, fontWeight: '700', lineHeight: 19 },
  taskMeta: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, marginTop: 2 },
  taskPatient: { color: Colors.gray400, fontSize: 12 },
  taskMrn: { color: Colors.gray600, fontSize: 11 },
  taskRight: { alignItems: 'flex-end', gap: 4 },
  priBadge: { borderWidth: 1, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  priText: { fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },
  dueText: { color: Colors.gray400, fontSize: 11, fontWeight: '600' },
  aiBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, alignSelf: 'flex-start', backgroundColor: Colors.tealDim2, borderWidth: 1, borderColor: `${Colors.teal}25`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  aiText: { color: Colors.teal, fontSize: 10, fontWeight: '700' },
  taskNote: { color: Colors.gray400, fontSize: 12, lineHeight: 17 },
  assigneeRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  assigneeText: { color: Colors.gray600, fontSize: 12, flex: 1 },
  inProgressChip: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: `${Colors.amber}18`, borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 2 },
  inProgressDot: { width: 5, height: 5, borderRadius: 2.5, backgroundColor: Colors.amber },
  inProgressText: { color: Colors.amber, fontSize: 10, fontWeight: '700' },
  taskActions: { flexDirection: 'row', gap: Spacing.sm },
  doneBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.teal, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  doneBtnText: { color: Colors.navy, fontWeight: '800', fontSize: 12 },
  startBtn: { backgroundColor: Colors.navyLight, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs },
  startBtnText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  viewBtn: { flex: 1, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.sm, paddingVertical: Spacing.xs, alignItems: 'center' },
  viewBtnText: { color: Colors.gray400, fontSize: 12, fontWeight: '600' },
  doneSection: { marginTop: Spacing.md, gap: Spacing.sm },
  doneSectionTitle: { color: Colors.gray600, fontSize: 13, fontWeight: '700', letterSpacing: 0.5 },
  doneRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.xs },
  doneRowText: { color: Colors.gray600, fontSize: 13, flex: 1, textDecorationLine: 'line-through' },
  doneRowPatient: { color: Colors.gray600, fontSize: 11 },
});
