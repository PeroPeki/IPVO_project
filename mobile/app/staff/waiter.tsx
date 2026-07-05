import { useCallback, useEffect, useState } from 'react';
import {
  Alert, FlatList, Pressable, Text, TextInput, View,
} from 'react-native';
import OrderCard from '../../components/OrderCard';
import { Colors } from '../../constants/colors';
import { useAuth } from '../../hooks/useAuth';
import { useSocketEvent } from '../../hooks/useSocket';
import { api, errorMessage } from '../../services/api';
import { joinWaiterRoom } from '../../services/socket';

/** Konobar: prijava PIN-om, real-time narudžbe svoje sekcije. */
export default function WaiterScreen() {
  const { staff, role, staffLogin, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [orders, setOrders] = useState<any[]>([]);

  const loggedIn = role === 'waiter' && staff;

  const loadOrders = useCallback(() => {
    api.get('/api/orders/waiter').then((r) => setOrders(r.data.orders)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!loggedIn) return;
    joinWaiterRoom(staff._id);
    loadOrders();
  }, [loggedIn, loadOrders]);

  // Nova/promijenjena narudžba stiže real-time preko Redis Pub/Sub → Socket.IO
  useSocketEvent('order_updated', useCallback(() => loadOrders(), [loadOrders]));

  async function login() {
    setError('');
    try {
      await staffLogin(email.trim(), pin);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function act(orderId: string, action: 'accept' | 'deliver') {
    try {
      await api.put(`/api/orders/${orderId}/${action}`);
      loadOrders();
    } catch (err: any) {
      Alert.alert('Greška', errorMessage(err));
    }
  }

  if (!loggedIn) {
    return (
      <View className="flex-1 bg-bgDark justify-center px-6">
        <Text className="text-textLight text-2xl font-extrabold mb-6">Prijava osoblja</Text>
        <TextInput
          className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3"
          placeholder="Email" placeholderTextColor={Colors.textMuted}
          autoCapitalize="none" value={email} onChangeText={setEmail}
        />
        <TextInput
          className="bg-bgCard text-textLight rounded-xl px-4 py-4 mb-3 border border-accent3 text-center text-2xl tracking-widest"
          placeholder="PIN" placeholderTextColor={Colors.textMuted}
          keyboardType="number-pad" maxLength={4} secureTextEntry
          value={pin} onChangeText={setPin}
        />
        {error ? <Text className="text-error mb-3">{error}</Text> : null}
        <Pressable className="bg-accent1 rounded-xl py-4 items-center" onPress={login} disabled={loading}>
          <Text className="text-white font-bold">Prijava</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-bgDark px-4 pt-4">
      <Text className="text-textLight text-xl font-extrabold mb-3">
        Aktivne narudžbe ({orders.length})
      </Text>
      <FlatList
        data={orders}
        keyExtractor={(o) => o._id}
        renderItem={({ item }) => (
          <OrderCard
            order={item}
            actionLabel={
              item.order_status === 'placed' ? 'Prihvati'
                : ['accepted', 'preparing'].includes(item.order_status) ? 'Dostavljeno' : undefined
            }
            onAction={() =>
              act(item._id, item.order_status === 'placed' ? 'accept' : 'deliver')
            }
          />
        )}
        ListEmptyComponent={
          <Text className="text-textMuted text-center mt-10">
            Nema aktivnih narudžbi u tvojoj sekciji. 🎉
          </Text>
        }
      />
    </View>
  );
}
