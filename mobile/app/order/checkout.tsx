import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, Text, View } from 'react-native';
import PaymentSheet from '../../components/PaymentSheet';
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
    <ScrollView className="flex-1 bg-bgDark px-4 pt-4">
      <Text className="text-textLight text-xl font-extrabold mb-3">Sažetak narudžbe</Text>
      <View className="bg-bgCard rounded-xl p-4 border border-accent3">
        {cart.items.map((i) => (
          <View key={i.menu_item_id} className="flex-row justify-between py-1">
            <Text className="text-textLight">{i.quantity}× {i.name}</Text>
            <Text className="text-textMuted">{(i.price * i.quantity).toFixed(2)} €</Text>
          </View>
        ))}
        <View className="flex-row justify-between pt-3 mt-2 border-t border-accent3/50">
          <Text className="text-textLight font-bold">Ukupno (prije kupona)</Text>
          <Text className="text-textLight font-extrabold">{cart.total().toFixed(2)} €</Text>
        </View>
        {result && result.coupon_applied > 0 && (
          <>
            <View className="flex-row justify-between mt-1">
              <Text className="text-accent1">VIP kupon</Text>
              <Text className="text-accent1">−{result.coupon_applied} €</Text>
            </View>
            <View className="flex-row justify-between mt-1">
              <Text className="text-textLight font-bold">Za platiti</Text>
              <Text className="text-textLight font-extrabold">{result.total} €</Text>
            </View>
          </>
        )}
      </View>

      <Text className="text-textLight text-lg font-bold mt-6 mb-2">Način plaćanja</Text>
      {methods.map((m) => (
        <Pressable
          key={m.value}
          className={`rounded-xl p-4 mb-2 border ${
            method === m.value ? 'border-accent1 bg-accent1/10' : 'border-accent3 bg-bgCard'
          }`}
          disabled={!!result}
          onPress={() => setMethod(m.value)}
        >
          <Text className={method === m.value ? 'text-accent1 font-bold' : 'text-textLight'}>
            {m.label}
          </Text>
        </Pressable>
      ))}

      <View className="mt-4 mb-12">
        {!result ? (
          <Pressable
            className="bg-accent1 rounded-xl py-4 items-center"
            onPress={placeOrder}
            disabled={placing}
          >
            <Text className="text-white font-bold text-base">
              {placing ? 'Slanje…' : 'Naruči'}
            </Text>
          </Pressable>
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
