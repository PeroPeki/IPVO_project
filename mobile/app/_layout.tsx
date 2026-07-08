import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold } from '@expo-google-fonts/inter';
import { Syne_600SemiBold, Syne_700Bold, Syne_800ExtraBold, useFonts } from '@expo-google-fonts/syne';
import { StripeProvider } from '@stripe/stripe-react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';
import { Colors } from '../constants/colors';
import '../global.css';

const STRIPE_PK = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? '';

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Syne_600SemiBold,
    Syne_700Bold,
    Syne_800ExtraBold,
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  // Zadrži crnu podlogu dok se fontovi ne učitaju — bez bijelog bljeska.
  if (!fontsLoaded) return <View style={{ flex: 1, backgroundColor: Colors.ink }} />;

  return (
    <StripeProvider publishableKey={STRIPE_PK} merchantIdentifier="merchant.hr.nightclubmanager">
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: Colors.ink },
          headerTintColor: Colors.white,
          headerTitleStyle: { fontFamily: 'Syne_700Bold' },
          headerShadowVisible: false,
          contentStyle: { backgroundColor: Colors.ink },
        }}
      >
        <Stack.Screen name="(auth)" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="club/[slug]" options={{ headerTransparent: true, title: '' }} />
        <Stack.Screen name="event/[id]" options={{ headerTransparent: true, title: '' }} />
        <Stack.Screen name="reservation/map/[event_id]" options={{ title: 'Odaberi stol' }} />
        <Stack.Screen name="reservation/confirm/[id]" options={{ title: 'Potvrda rezervacije' }} />
        <Stack.Screen name="order/menu" options={{ title: 'Meni pića' }} />
        <Stack.Screen name="order/cart" options={{ title: 'Košarica' }} />
        <Stack.Screen name="order/checkout" options={{ title: 'Naplata' }} />
      </Stack>
    </StripeProvider>
  );
}
