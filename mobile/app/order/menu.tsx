import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import MenuCategory from '../../components/MenuCategory';
import { useCart } from '../../hooks/useCart';
import { api, errorMessage } from '../../services/api';

/** Meni pića kluba — dodavanje u košaricu. */
export default function OrderMenu() {
  const router = useRouter();
  const cart = useCart();
  const [menu, setMenu] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!cart.clubId) {
      setError('Naručivanje pića dostupno je samo gostima s rezerviranim stolom.');
      return;
    }
    api.get(`/api/menu/club/${cart.clubId}`)
      .then((res) => setMenu(res.data))
      .catch((err) => setError(errorMessage(err)));
  }, [cart.clubId]);

  const itemCount = cart.items.reduce((s, i) => s + i.quantity, 0);

  return (
    <View className="flex-1 bg-bgDark">
      <ScrollView className="px-4 pt-4">
        {error ? <Text className="text-error mt-4">{error}</Text> : null}
        {menu?.categories?.map((cat: any) => (
          <MenuCategory key={cat.id} category={cat} />
        ))}
        <View className="h-28" />
      </ScrollView>

      {itemCount > 0 && (
        <View className="absolute bottom-0 left-0 right-0 p-4 bg-bgCard border-t border-accent3">
          <Pressable
            className="bg-accent1 rounded-xl py-4 items-center"
            onPress={() => router.push('/order/cart')}
          >
            <Text className="text-white font-bold text-base">
              Košarica ({itemCount}) · {cart.total().toFixed(2)} €
            </Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}
