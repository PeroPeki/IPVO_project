import { useRouter } from 'expo-router';
import { FlatList, Text, View } from 'react-native';
import PressableScale from '../../components/ui/PressableScale';
import { glow } from '../../constants/theme';
import { useCart } from '../../hooks/useCart';

/** Košarica — pregled i uređivanje količina prije naplate. */
export default function Cart() {
  const router = useRouter();
  const cart = useCart();

  return (
    <View className="flex-1 bg-ink px-5 pt-5">
      <FlatList
        data={cart.items}
        keyExtractor={(i) => i.menu_item_id}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => (
          <View className="bg-surface rounded-2xl p-4 mb-2.5 border border-line flex-row items-center">
            <View className="flex-1">
              <Text className="text-white font-bodySb">{item.name}</Text>
              <Text className="text-muted font-body text-xs">{item.price} € / kom</Text>
            </View>
            <View className="flex-row items-center gap-3">
              <PressableScale
                className="bg-surfaceHi w-9 h-9 rounded-full items-center justify-center border border-line"
                onPress={() => cart.setQuantity(item.menu_item_id, item.quantity - 1)}
              >
                <Text className="text-white font-bodyBd text-lg">−</Text>
              </PressableScale>
              <Text className="text-white font-heading w-6 text-center">{item.quantity}</Text>
              <PressableScale
                className="bg-neon w-9 h-9 rounded-full items-center justify-center"
                onPress={() => cart.setQuantity(item.menu_item_id, item.quantity + 1)}
              >
                <Text className="text-white font-bodyBd text-lg">+</Text>
              </PressableScale>
            </View>
            <Text className="text-white font-heading w-16 text-right">
              {(item.price * item.quantity).toFixed(2)} €
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <Text className="text-muted font-body text-center mt-10">Košarica je prazna.</Text>
        }
      />

      {cart.items.length > 0 && (
        <View className="pb-8">
          <View className="flex-row justify-between items-center py-4">
            <Text className="text-muted font-body text-lg">Ukupno</Text>
            <Text className="text-white font-display text-2xl">{cart.total().toFixed(2)} €</Text>
          </View>
          <Text className="text-muted font-body text-xs mb-3 text-center">
            VIP kupon (ako ga imaš) automatski se primjenjuje pri naplati.
            Kupon je vezan uz Vas osobno i ne može se dijeliti s drugim gostima.
          </Text>
          <PressableScale
            className="bg-neon rounded-2xl py-4 items-center"
            style={glow}
            onPress={() => router.push('/order/checkout')}
          >
            <Text className="text-white font-bodyBd text-base">Na naplatu</Text>
          </PressableScale>
        </View>
      )}
    </View>
  );
}
