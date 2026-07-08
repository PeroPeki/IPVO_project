import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import PaymentSheet from '../../../components/PaymentSheet';
import PressableScale from '../../../components/ui/PressableScale';
import { glow } from '../../../constants/theme';
import { useCart } from '../../../hooks/useCart';
import { api, errorMessage } from '../../../services/api';

const STATUS: Record<string, { label: string; cls: string }> = {
  confirmed: { label: 'Potvrđena', cls: 'text-success' },
  checked_in: { label: 'Ušli ste', cls: 'text-success' },
  pending: { label: 'Čeka depozit', cls: 'text-warning' },
  cancelled: { label: 'Otkazana', cls: 'text-error' },
};

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

  if (!reservation) return <View className="flex-1 bg-ink" />;

  const isVip = reservation.table_type === 'vip_separe';
  const needsDeposit = isVip && !reservation.deposit_paid && reservation.deposit_amount > 0;
  const st = STATUS[reservation.status] ?? { label: reservation.status, cls: 'text-muted' };

  return (
    <ScrollView className="flex-1 bg-ink px-5 pt-5" showsVerticalScrollIndicator={false}>
      <View className="bg-surface rounded-3xl p-6 border border-line">
        <Text className="text-white font-display text-2xl uppercase" style={{ letterSpacing: 0.4 }}>
          {isVip ? 'VIP separé' : 'Stol'} {reservation.table_label}
        </Text>
        <Text className="text-muted font-body mt-1">{reservation.event?.name}</Text>
        <Text className="text-muted font-body">
          {reservation.event?.date ? new Date(reservation.event.date).toLocaleString('hr-HR') : ''}
        </Text>

        <View className="flex-row justify-between mt-4 pt-4 border-t border-line">
          <Text className="text-muted font-body">Status</Text>
          <Text className={`font-bodyBd ${st.cls}`}>{st.label}</Text>
        </View>
        <View className="flex-row justify-between mt-2">
          <Text className="text-muted font-body">Broj gostiju</Text>
          <Text className="text-white font-bodySb">{reservation.guests_count}</Text>
        </View>
        {isVip && (
          <>
            <View className="flex-row justify-between mt-2">
              <Text className="text-muted font-body">Depozit</Text>
              <Text className="text-white font-bodySb">
                {reservation.deposit_amount} € {reservation.deposit_paid ? '✓ plaćen' : ''}
              </Text>
            </View>
            {reservation.deposit_paid && (
              <View className="flex-row justify-between mt-2">
                <Text className="text-muted font-body">Kupon za piće</Text>
                <Text className="text-neon font-bodyBd">{reservation.deposit_coupon_remaining} €</Text>
              </View>
            )}
          </>
        )}
      </View>

      {needsDeposit && !deposit && (
        <PressableScale className="bg-neon rounded-2xl py-4 items-center mt-4" style={glow} onPress={startDeposit}>
          <Text className="text-white font-bodyBd text-base">
            Plati depozit ({reservation.deposit_amount} €)
          </Text>
        </PressableScale>
      )}

      {deposit && (
        <View className="mt-4">
          <Text className="text-warning font-body text-xs mb-3 text-center">{deposit.notice}</Text>
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
        <PressableScale
          className="border border-neon/60 bg-neon/10 rounded-2xl py-4 items-center mt-4"
          onPress={startOrdering}
        >
          <Text className="text-white font-bodyBd text-base">Naruči piće za stol</Text>
        </PressableScale>
      )}

      {['pending', 'confirmed'].includes(reservation.status) && (
        <Pressable className="py-4 items-center mt-2 mb-10" onPress={cancel}>
          <Text className="text-error font-bodySb">Otkaži rezervaciju</Text>
        </Pressable>
      )}
    </ScrollView>
  );
}
