import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import MenuCategory from '../../components/MenuCategory';
import PressableScale from '../../components/ui/PressableScale';
import { glow } from '../../constants/theme';
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
    <View className="flex-1 bg-ink">
      <ScrollView className="px-5 pt-5" showsVerticalScrollIndicator={false}>
        {error ? <Text className="text-error font-body mt-4">{error}</Text> : null}
        {menu?.categories?.map((cat: any) => (
          <MenuCategory key={cat.id} category={cat} />
        ))}
        <View className="h-28" />
      </ScrollView>

      {itemCount > 0 && (
        <View className="absolute bottom-0 left-0 right-0 p-4 bg-inkSoft border-t border-line">
          <PressableScale
            className="bg-neon rounded-2xl py-4 items-center"
            style={glow}
            onPress={() => router.push('/order/cart')}
          >
            <Text className="text-white font-bodyBd text-base">
              Košarica ({itemCount})  ·  {cart.total().toFixed(2)} €
            </Text>
          </PressableScale>
        </View>
      )}
    </View>
  );
}
