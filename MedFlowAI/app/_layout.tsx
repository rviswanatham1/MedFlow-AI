import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Colors } from '../constants/theme';
import { AppProvider } from '../context/AppContext';

export default function RootLayout() {
  return (
    <SafeAreaProvider>
    <AppProvider>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: Colors.navy },
          animation: 'fade_from_bottom',
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="auth/login" />
        <Stack.Screen name="auth/register" />
        <Stack.Screen name="patient/home" />
        <Stack.Screen name="patient/symptom-input" />
        <Stack.Screen name="patient/triage-result" />
        <Stack.Screen name="patient/wait-time" />
        <Stack.Screen name="patient/book-appointment" />
        <Stack.Screen name="patient/notifications" />
        <Stack.Screen name="patient/records" />
        <Stack.Screen name="patient/price-estimate" />
        <Stack.Screen name="patient/referrals" />
        <Stack.Screen name="staff/dashboard" />
        <Stack.Screen name="staff/patient-queue" />
        <Stack.Screen name="staff/patient-detail" />
        <Stack.Screen name="staff/analytics" />
        <Stack.Screen name="staff/integrations" />
        <Stack.Screen name="staff/patient-search" />
        <Stack.Screen name="staff/worklist" />
        <Stack.Screen name="staff/resource-allocation" />
      </Stack>
    </AppProvider>
    </SafeAreaProvider>
  );
}
