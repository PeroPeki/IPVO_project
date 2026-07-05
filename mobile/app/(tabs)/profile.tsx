import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { api } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';

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
    <View className="flex-1 bg-bgDark px-4 pt-6">
      <View className="bg-bgCard rounded-2xl p-5 border border-accent3 items-center">
        <View className="w-16 h-16 rounded-full bg-accent3 items-center justify-center mb-3">
          <Text className="text-accent1 text-2xl font-extrabold">
            {(user?.name ?? '?')[0]?.toUpperCase()}
          </Text>
        </View>
        <Text className="text-textLight text-xl font-bold">{user?.name ?? 'Korisnik'}</Text>
        <Text className="text-textMuted">{user?.email}</Text>
      </View>

      <Text className="text-textLight text-lg font-bold mt-6 mb-2">Zadnje narudžbe</Text>
      {orders.map((o) => (
        <View key={o._id} className="bg-bgCard rounded-xl p-3 mb-2 border border-accent3">
          <Text className="text-textLight">
            {o.event?.name ?? 'Event'} · {o.total} €
          </Text>
          <Text className="text-textMuted text-xs">
            {new Date(o.created_at).toLocaleString('hr-HR')} · {o.order_status}
          </Text>
        </View>
      ))}
      {orders.length === 0 && <Text className="text-textMuted">Nema narudžbi.</Text>}

      <Pressable className="bg-error/20 rounded-xl py-4 items-center mt-8" onPress={doLogout}>
        <Text className="text-error font-bold">Odjava</Text>
      </Pressable>
    </View>
  );
}
