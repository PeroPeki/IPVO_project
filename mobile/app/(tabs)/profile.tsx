import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FadeIn from '../../components/ui/FadeIn';
import PressableScale from '../../components/ui/PressableScale';
import ScreenHeader from '../../components/ui/ScreenHeader';
import { glow } from '../../constants/theme';
import { useAuth } from '../../hooks/useAuth';
import { api } from '../../services/api';

export default function Profile() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);

  useEffect(() => {
    api.get('/api/orders/my').then((r) => setOrders(r.data.orders.slice(0, 5))).catch(() => {});
  }, []);

  async function doLogout() {
    await logout();
    router.replace('/(auth)/login');
  }

  return (
    <SafeAreaView edges={['top']} className="flex-1 bg-ink">
      <ScrollView className="px-5" showsVerticalScrollIndicator={false}>
        <ScreenHeader eyebrow="Račun" title="Profil" />

        <FadeIn>
          <View className="items-center bg-surface rounded-3xl p-7 border border-line">
            <View
              className="w-20 h-20 rounded-full bg-neon/15 border-2 border-neon items-center justify-center mb-4"
              style={glow}
            >
              <Text className="text-white font-display text-3xl">
                {(user?.name ?? '?')[0]?.toUpperCase()}
              </Text>
            </View>
            <Text className="text-white font-heading text-xl uppercase" style={{ letterSpacing: 0.3 }}>
              {user?.name ?? 'Korisnik'}
            </Text>
            <Text className="text-muted font-body mt-1">{user?.email}</Text>
          </View>
        </FadeIn>

        <Text className="text-white font-display text-[22px] uppercase mt-9 mb-4" style={{ letterSpacing: 0.5 }}>
          Zadnje narudžbe
        </Text>
        {orders.map((o, i) => (
          <FadeIn key={o._id} delay={Math.min(i, 5) * 50}>
            <View className="bg-surface rounded-2xl p-4 mb-2.5 border border-line flex-row items-center justify-between">
              <View className="flex-1 mr-3">
                <Text className="text-text font-bodySb" numberOfLines={1}>{o.event?.name ?? 'Event'}</Text>
                <Text className="text-muted font-body text-xs mt-0.5">
                  {new Date(o.created_at).toLocaleString('hr-HR')}  ·  {o.order_status}
                </Text>
              </View>
              <Text className="text-white font-heading">{o.total} €</Text>
            </View>
          </FadeIn>
        ))}
        {orders.length === 0 && <Text className="text-muted font-body">Nema narudžbi.</Text>}

        <PressableScale
          className="bg-error/10 border border-error/30 rounded-2xl py-4 items-center mt-9 mb-10"
          onPress={doLogout}
        >
          <Text className="text-error font-bodyBd">Odjava</Text>
        </PressableScale>
      </ScrollView>
    </SafeAreaView>
  );
}
