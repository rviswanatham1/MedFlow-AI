import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  SafeAreaView, ActivityIndicator, RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Colors, Spacing, Radius } from '../../constants/theme';

// ─── BACKEND INTEGRATION ──────────────────────────────────────────────────────
// This screen connects to YOUR backend. Here's exactly what your friend needs:
//
// 1. REST endpoint:
//    GET  /api/notifications?patient_id=:id&limit=50
//    Returns: { notifications: Notification[], unread_count: number }
//
// 2. Mark read:
//    PATCH /api/notifications/:id/read
//    PATCH /api/notifications/read-all?patient_id=:id
//
// 3. Push notifications (optional - for real-time):
//    Use Expo Push Notifications: https://docs.expo.dev/push-notifications/overview/
//    Your backend sends to: https://exp.host/--/api/v2/push/send
//    Payload: { to: expoPushToken, title, body, data: { notif_id, type } }
//
// 4. WebSocket (optional - for live queue updates):
//    WS /ws/notifications?patient_id=:id
//    Backend emits events when triage approved, queue position changes, etc.
//
// HOW NOTIFICATIONS GET CREATED ON THE BACKEND:
//    - Triage approved → emit 'triage_complete' notification
//    - Lab result arrives (HL7 ORU) → emit 'lab_ready' notification
//    - Insurance verified (X12 271) → emit 'insurance_verified' notification
//    - Queue position < 3 → emit 'queue_alert' notification
//    - Appointment reminder (cron) → emit 'appointment_reminder' notification
// ─────────────────────────────────────────────────────────────────────────────

const API_BASE = 'http://YOUR_BACKEND_URL'; // ← your friend replaces this
const PATIENT_ID = 'PT-0042'; // ← replace with auth context / AsyncStorage

type NotifType = 'lab' | 'insurance' | 'reminder' | 'appointment' | 'triage' | 'alert';

interface Notification {
  id: string;
  type: NotifType;
  title: string;
  body: string;
  created_at: string;  // ISO timestamp from backend
  read: boolean;
  meta?: Record<string, string>; // e.g. { referral_id, appointment_id }
}

// ── MOCK DATA used until backend is ready ──
// Replace fetchNotifications() with real API call — structure is identical
const MOCK: Notification[] = [
  { id: '1', type: 'lab',         title: 'Lab Results Ready',           body: 'Your CBC panel results are available.',                           created_at: new Date(Date.now() - 2*60*60*1000).toISOString(),   read: false },
  { id: '2', type: 'triage',      title: 'Triage Complete',             body: 'Assessment reviewed and approved by Dr. Patel. Pathway: Urgent Care.', created_at: new Date(Date.now() - 3*60*60*1000).toISOString(),   read: false },
  { id: '3', type: 'insurance',   title: 'Insurance Verified',          body: 'Blue Cross Blue Shield eligibility pre-verified for your visit.', created_at: new Date(Date.now() - 24*60*60*1000).toISOString(),  read: true  },
  { id: '4', type: 'appointment', title: 'Appointment Reminder',        body: 'Follow-up with Dr. Patel tomorrow at 10:00 AM.',                 created_at: new Date(Date.now() - 25*60*60*1000).toISOString(),  read: true  },
  { id: '5', type: 'alert',       title: 'Queue Update',                body: 'You are now #2 in the Urgent Care queue. ~5 minutes.',           created_at: new Date(Date.now() - 48*60*60*1000).toISOString(),  read: true  },
  { id: '6', type: 'reminder',    title: 'Flu Shot Available',          body: 'Fast-pass flu shots available — no appointment needed.',         created_at: new Date(Date.now() - 15*24*60*60*1000).toISOString(),read: true  },
];

const TYPE_CFG: Record<NotifType, { icon: string; color: string }> = {
  lab:         { icon: 'flask-outline',           color: Colors.teal  },
  insurance:   { icon: 'shield-check',            color: Colors.green },
  reminder:    { icon: 'needle',                  color: Colors.amber },
  appointment: { icon: 'calendar-check',          color: Colors.blue  },
  triage:      { icon: 'clipboard-pulse-outline', color: Colors.teal  },
  alert:       { icon: 'bell-ring-outline',       color: Colors.red   },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins < 60)  return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

type Filter = 'all' | 'unread';

export default function NotificationsScreen() {
  const router = useRouter();
  const [notifs, setNotifs]       = useState<Notification[]>([]);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter]       = useState<Filter>('all');
  const [error, setError]         = useState<string | null>(null);

  const fetchNotifications = useCallback(async () => {
    try {
      // ── REAL API CALL (uncomment when backend is ready) ──
      // const res = await fetch(`${API_BASE}/api/notifications?patient_id=${PATIENT_ID}&limit=50`, {
      //   headers: { Authorization: `Bearer ${await getToken()}` },
      // });
      // if (!res.ok) throw new Error('Failed to fetch');
      // const data = await res.json();
      // setNotifs(data.notifications);

      // ── MOCK (remove when backend ready) ──
      await new Promise(r => setTimeout(r, 600)); // simulate network
      setNotifs(MOCK);
      setError(null);
    } catch (e) {
      setError('Could not load notifications. Pull to retry.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchNotifications(); }, []);

  const onRefresh = () => { setRefreshing(true); fetchNotifications(); };

  const markRead = async (id: string) => {
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    // TODO: PATCH /api/notifications/:id/read
  };

  const markAllRead = async () => {
    setNotifs(prev => prev.map(n => ({ ...n, read: true })));
    // TODO: PATCH /api/notifications/read-all?patient_id=${PATIENT_ID}
  };

  const displayed  = filter === 'unread' ? notifs.filter(n => !n.read) : notifs;
  const unreadCount = notifs.filter(n => !n.read).length;

  const renderItem = ({ item }: { item: Notification }) => {
    const cfg = TYPE_CFG[item.type];
    return (
      <TouchableOpacity onPress={() => markRead(item.id)} activeOpacity={0.75}>
        <View style={[styles.notifItem, !item.read && styles.notifItemUnread]}>
          <View style={styles.unreadCol}>
            {!item.read && <View style={styles.unreadDot} />}
          </View>
          <View style={[styles.iconBg, { backgroundColor: `${cfg.color}18` }]}>
            <MaterialCommunityIcons name={cfg.icon as any} size={20} color={cfg.color} />
          </View>
          <View style={styles.notifContent}>
            <View style={styles.notifTitleRow}>
              <Text style={[styles.notifTitle, !item.read && styles.notifTitleUnread]} numberOfLines={1}>
                {item.title}
              </Text>
              <Text style={styles.notifTime}>{timeAgo(item.created_at)}</Text>
            </View>
            <Text style={styles.notifBody} numberOfLines={2}>{item.body}</Text>
          </View>
          <Ionicons name="chevron-forward" size={14} color={Colors.gray600} />
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.navy }}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={22} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Notifications</Text>
        {unreadCount > 0
          ? <TouchableOpacity onPress={markAllRead}><Text style={styles.markAllText}>Mark all read</Text></TouchableOpacity>
          : <View style={{ width: 80 }} />
        }
      </View>

      {/* Filter */}
      <View style={styles.filterBar}>
        <TouchableOpacity style={[styles.filterChip, filter === 'all' && styles.filterChipActive]} onPress={() => setFilter('all')}>
          <Text style={[styles.filterText, filter === 'all' && styles.filterTextActive]}>All</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.filterChip, filter === 'unread' && styles.filterChipActive]} onPress={() => setFilter('unread')}>
          <Text style={[styles.filterText, filter === 'unread' && styles.filterTextActive]}>Unread</Text>
          {unreadCount > 0 && (
            <View style={styles.countBadge}><Text style={styles.countBadgeText}>{unreadCount}</Text></View>
          )}
        </TouchableOpacity>
      </View>

      {/* States */}
      {loading && (
        <View style={styles.centered}>
          <ActivityIndicator color={Colors.teal} size="large" />
        </View>
      )}

      {!loading && error && (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="wifi-off" size={40} color={Colors.gray600} />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={fetchNotifications}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!loading && !error && displayed.length === 0 && (
        <View style={styles.centered}>
          <MaterialCommunityIcons name="bell-off-outline" size={48} color={Colors.gray600} />
          <Text style={styles.emptyTitle}>All caught up</Text>
          <Text style={styles.emptyText}>No {filter === 'unread' ? 'unread ' : ''}notifications</Text>
        </View>
      )}

      {!loading && !error && displayed.length > 0 && (
        <FlatList
          data={displayed}
          keyExtractor={item => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.teal} />}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: Spacing.lg, paddingTop: Spacing.md, paddingBottom: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder },
  backBtn: { width: 40, height: 40, justifyContent: 'center' },
  headerTitle: { color: Colors.white, fontSize: 17, fontWeight: '700' },
  markAllText: { color: Colors.teal, fontSize: 13, fontWeight: '600', width: 80, textAlign: 'right' },
  filterBar: { flexDirection: 'row', gap: Spacing.sm, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, borderBottomWidth: 1, borderBottomColor: Colors.glassBorder, backgroundColor: Colors.navyMid },
  filterChip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs + 2, backgroundColor: Colors.glass, borderWidth: 1, borderColor: Colors.glassBorder, borderRadius: Radius.full },
  filterChipActive: { backgroundColor: Colors.tealDim, borderColor: Colors.teal },
  filterText: { color: Colors.gray400, fontSize: 13, fontWeight: '600' },
  filterTextActive: { color: Colors.teal },
  countBadge: { backgroundColor: Colors.red, borderRadius: 99, paddingHorizontal: 6, paddingVertical: 1, minWidth: 18, alignItems: 'center' },
  countBadgeText: { color: Colors.white, fontSize: 10, fontWeight: '800' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: Spacing.md, padding: Spacing.xl },
  errorText: { color: Colors.gray400, fontSize: 14, textAlign: 'center' },
  retryBtn: { backgroundColor: Colors.tealDim, borderWidth: 1, borderColor: `${Colors.teal}44`, borderRadius: Radius.md, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm },
  retryText: { color: Colors.teal, fontWeight: '700', fontSize: 14 },
  emptyTitle: { color: Colors.white, fontSize: 18, fontWeight: '700' },
  emptyText: { color: Colors.gray400, fontSize: 14 },
  list: { paddingBottom: Spacing.xxl },
  notifItem: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, gap: Spacing.sm },
  notifItemUnread: { backgroundColor: `${Colors.teal}06` },
  unreadCol: { width: 10, alignItems: 'center' },
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.teal },
  iconBg: { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  notifContent: { flex: 1, gap: 3 },
  notifTitleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: Spacing.sm },
  notifTitle: { color: Colors.gray400, fontSize: 14, fontWeight: '600', flex: 1 },
  notifTitleUnread: { color: Colors.white, fontWeight: '700' },
  notifTime: { color: Colors.gray600, fontSize: 11, flexShrink: 0 },
  notifBody: { color: Colors.gray600, fontSize: 12, lineHeight: 17 },
  separator: { height: 1, backgroundColor: Colors.glassBorder, marginHorizontal: Spacing.lg },
});
