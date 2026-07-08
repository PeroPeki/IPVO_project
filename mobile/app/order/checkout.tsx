import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, Text, View } from 'react-native';
import PaymentSheet from '../../components/PaymentSheet';
import PressableScale from '../../components/ui/PressableScale';
import { glow } from '../../constants/theme';
import { useCart } from '../../hooks/useCart';
import { api, errorMessage } from '../../services/api';

type Method = 'card' | 'apple_pay' | 'google_pay' | 'cash';

/** Naplata narudžbe — Stripe (kartica/wallet) ili gotovina konobaru. */
export default function Checkout() {
  const router = useRouter();
  const cart = useCart();
  const [method, setMethod] = useState<Method>('card');
  const [result, setResult] = useState<any>(null);
  const [placing, setPlacing] = useState(false);

  async function placeOrder() {
    setPlacing(true);
    try {
      const res = await api.post('/api/orders', {
        reservation_id: cart.reservationId,
        items: cart.items.map((i) => ({ menu_item_id: i.menu_item_id, quantity: i.quantity })),
        payment_method: method,
      });
      setResult(res.data);
      if (method === 'cash' || res.data.payment_status === 'paid') {
        cart.clear();
        Alert.alert(
          'Narudžba poslana',
          res.data.payment_status === 'paid'
            ? 'Kupon je pokrio cijelu narudžbu. Konobar stiže!'
            : 'Konobar stiže — plaćanje gotovinom pri dostavi.',
        );
        router.dismissAll();
      }
    } catch (err: any) {
      Alert.alert('Narudžba nije moguća', errorMessage(err));
    } finally {
      setPlacing(false);
    }
  }

  const methods: { value: Method; label: string }[] = [
    { value: 'card', label: 'Kartica' },
    { value: 'apple_pay', label: 'Apple Pay' },
    { value: 'google_pay', label: 'Google Pay' },
    { value: 'cash', label: 'Gotovina konobaru' },
  ];

  return (
    <ScrollView className="flex-1 bg-ink px-5 pt-5" showsVerticalScrollIndicator={false}>
      <Text className="text-white font-display text-2xl uppercase mb-3" style={{ letterSpacing: 0.5 }}>Sažetak</Text>
      <View className="bg-surface rounded-2xl p-5 border border-line">
        {cart.items.map((i) => (
          <View key={i.menu_item_id} className="flex-row justify-between py-1">
            <Text className="text-text font-body">{i.quantity}× {i.name}</Text>
            <Text className="text-muted font-body">{(i.price * i.quantity).toFixed(2)} €</Text>
          </View>
        ))}
        <View className="flex-row justify-between pt-3 mt-2 border-t border-line">
          <Text className="text-text font-bodySb">Ukupno (prije kupona)</Text>
          <Text className="text-white font-heading">{cart.total().toFixed(2)} €</Text>
        </View>
        {result && result.coupon_applied > 0 && (
          <>
            <View className="flex-row justify-between mt-2">
              <Text className="text-neon font-bodySb">VIP kupon</Text>
              <Text className="text-neon font-bodySb">−{result.coupon_applied} €</Text>
            </View>
            <View className="flex-row justify-between mt-1">
              <Text className="text-text font-bodySb">Za platiti</Text>
              <Text className="text-white font-heading">{result.total} €</Text>
            </View>
          </>
        )}
      </View>

      <Text className="text-white font-display text-[22px] uppercase mt-7 mb-3" style={{ letterSpacing: 0.5 }}>Plaćanje</Text>
      {methods.map((m) => {
        const active = method === m.value;
        return (
          <PressableScale
            key={m.value}
            className={`rounded-2xl p-4 mb-2.5 border ${active ? 'border-neon bg-neon/10' : 'border-line bg-surface'}`}
            disabled={!!result}
            onPress={() => setMethod(m.value)}
          >
            <Text className={active ? 'text-white font-bodyBd' : 'text-text font-bodyMd'}>{m.label}</Text>
          </PressableScale>
        );
      })}

      <View className="mt-4 mb-14">
        {!result ? (
          <PressableScale
            className="bg-neon rounded-2xl py-4 items-center"
            style={glow}
            onPress={placeOrder}
            disabled={placing}
          >
            <Text className="text-white font-bodyBd text-base">{placing ? 'Slanje…' : 'Naruči'}</Text>
          </PressableScale>
        ) : result.client_secret ? (
          <PaymentSheet
            clientSecret={result.client_secret}
            label={`Plati ${result.total} €`}
            onSuccess={() => {
              cart.clear();
              Alert.alert('Uspjeh', 'Narudžba plaćena — konobar stiže!');
              router.dismissAll();
            }}
            onError={(msg) => Alert.alert('Plaćanje nije uspjelo', msg)}
          />
        ) : null}
      </View>
    </ScrollView>
  );
}
