import { StripeProvider } from '@stripe/stripe-react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Colors } from '../constants/colors';
import '../global.css';

const STRIPE_PK = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? '';

export default function RootLayout() {
  return (
    <StripeProvider publishableKey={STRIPE_PK} merchantIdentifier="merchant.hr.nightclubmanager">
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: Colors.bgCard },
          headerTintColor: Colors.textLight,
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: Colors.bgDark },
        }}
      >
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="club/[slug]" options={{ title: 'Klub' }} />
        <Stack.Screen name="event/[id]" options={{ title: 'Event' }} />
        <Stack.Screen name="reservation/map/[event_id]" options={{ title: 'Odaberi stol' }} />
        <Stack.Screen name="reservation/confirm/[id]" options={{ title: 'Potvrda rezervacije' }} />
        <Stack.Screen name="order/menu" options={{ title: 'Meni pića' }} />
        <Stack.Screen name="order/cart" options={{ title: 'Košarica' }} />
        <Stack.Screen name="order/checkout" options={{ title: 'Naplata' }} />
        <Stack.Screen name="staff/hostess" options={{ title: 'Hostesa' }} />
        <Stack.Screen name="staff/waiter" options={{ title: 'Konobar' }} />
      </Stack>
    </StripeProvider>
  );
}
