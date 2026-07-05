import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import PaymentSheet from '../../../components/PaymentSheet';
import { useCart } from '../../../hooks/useCart';
import { api, errorMessage } from '../../../services/api';

/** Potvrda rezervacije + plaćanje depozita za VIP separé + ulaz u naručivanje. */
export default function ReservationConfirm() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const cart = useCart();
  const [reservation, setReservation] = useState<any>(null);
  const [deposit, setDeposit] = useState<{ clientSecret: string; notice: string } | null>(null);

  function load() {
    api.get('/api/reservations/my').then((res) => {
      const r = res.data.reservations.find((x: any) => x._id === id);
      setReservation(r ?? null);
    }).catch(() => {});
  }

  useEffect(load, [id]);

  async function startDeposit() {
    try {
      const res = await api.post(`/api/reservations/${id}/deposit`);
      setDeposit({ clientSecret: res.data.client_secret, notice: res.data.coupon_notice });
    } catch (err: any) {
      Alert.alert('Greška', errorMessage(err));
    }
  }

  async function cancel() {
    Alert.alert('Otkazivanje', 'Sigurno želiš otkazati rezervaciju?', [
      { text: 'Ne' },
      {
        text: 'Da, otkaži',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.post(`/api/reservations/${id}/cancel`);
            router.back();
          } catch (err: any) {
            Alert.alert('Greška', errorMessage(err));
          }
        },
      },
    ]);
  }

  function startOrdering() {
    cart.setContext(String(id), String(reservation.event_id), String(reservation.club_id));
    cart.clear();
    router.push('/order/menu');
  }

  if (!reservation) return <View className="flex-1 bg-bgDark" />;

  const isVip = reservation.table_type === 'vip_separe';
  const needsDeposit = isVip && !reservation.deposit_paid && reservation.deposit_amount > 0;

  return (
    <ScrollView className="flex-1 bg-bgDark px-4 pt-4">
      <View className="bg-bgCard rounded-2xl p-5 border border-accent3">
        <Text className="text-textLight text-2xl font-extrabold">
          {isVip ? 'VIP separé' : 'Stol'} {reservation.table_label}
        </Text>
        <Text className="text-textMuted mt-1">{reservation.event?.name}</Text>
        <Text className="text-textMuted">
          {reservation.event?.date ? new Date(reservation.event.date).toLocaleString('hr-HR') : ''}
        </Text>

        <View className="flex-row justify-between mt-4 pt-4 border-t border-accent3/50">
          <Text className="text-textMuted">Status</Text>
          <Text className={`font-bold ${
            reservation.status === 'confirmed' || reservation.status === 'checked_in'
              ? 'text-success' : reservation.status === 'pending' ? 'text-warning' : 'text-error'
          }`}>
            {reservation.status === 'pending' ? 'Čeka depozit'
              : reservation.status === 'confirmed' ? 'Potvrđena'
              : reservation.status === 'checked_in' ? 'Ušli ste' : 'Otkazana'}
          </Text>
        </View>
        <View className="flex-row justify-between mt-2">
          <Text className="text-textMuted">Broj gostiju</Text>
          <Text className="text-textLight font-semibold">{reservation.guests_count}</Text>
        </View>
        {isVip && (
          <>
            <View className="flex-row justify-between mt-2">
              <Text className="text-textMuted">Depozit</Text>
              <Text className="text-textLight font-semibold">
                {reservation.deposit_amount} € {reservation.deposit_paid ? '✓ plaćen' : ''}
              </Text>
            </View>
            {reservation.deposit_paid && (
              <View className="flex-row justify-between mt-2">
                <Text className="text-textMuted">Kupon za piće</Text>
                <Text className="text-accent1 font-bold">{reservation.deposit_coupon_remaining} €</Text>
              </View>
            )}
          </>
        )}
      </View>

      {needsDeposit && !deposit && (
        <Pressable className="bg-accent1 rounded-xl py-4 items-center mt-4" onPress={startDeposit}>
          <Text className="text-white font-bold text-base">
            Plati depozit ({reservation.deposit_amount} €)
          </Text>
        </Pressable>
      )}

      {deposit && (
        <View className="mt-4">
          <Text className="text-warning text-xs mb-3 text-center">{deposit.notice}</Text>
          <PaymentSheet
            clientSecret={deposit.clientSecret}
            label={`Plati depozit ${reservation.deposit_amount} €`}
            onSuccess={() => {
              setDeposit(null);
              Alert.alert('Uspjeh', 'Depozit plaćen — rezervacija je potvrđena!');
              load();
            }}
            onError={(msg) => Alert.alert('Plaćanje nije uspjelo', msg)}
          />
        </View>
      )}

      {(reservation.status === 'confirmed' || reservation.status === 'checked_in') && (
        <Pressable className="bg-accent2 rounded-xl py-4 items-center mt-4" onPress={startOrdering}>
          <Text className="text-white font-bold text-base">Naruči piće za stol</Text>
        </Pressable>
      )}

      {['pending', 'confirmed'].includes(reservation.status) && (
        <Pressable className="py-4 items-center mt-2 mb-10" onPress={cancel}>
          <Text className="text-error font-semibold">Otkaži rezervaciju</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}
