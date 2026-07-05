import { useRouter } from 'expo-router';
import { FlatList, Pressable, Text, View } from 'react-native';
import { useCart } from '../../hooks/useCart';

/** Košarica — pregled i uređivanje količina prije naplate. */
export default function Cart() {
  const router = useRouter();
  const cart = useCart();

  return (
    <View className="flex-1 bg-bgDark px-4 pt-4">
      <FlatList
        data={cart.items}
        keyExtractor={(i) => i.menu_item_id}
        renderItem={({ item }) => (
          <View className="bg-bgCard rounded-xl p-4 mb-2 border border-accent3 flex-row items-center">
            <View className="flex-1">
              <Text className="text-textLight font-semibold">{item.name}</Text>
              <Text className="text-textMuted text-xs">{item.price} € / kom</Text>
            </View>
            <View className="flex-row items-center gap-3">
              <Pressable
                className="bg-accent3 w-8 h-8 rounded-full items-center justify-center"
                onPress={() => cart.setQuantity(item.menu_item_id, item.quantity - 1)}
              >
                <Text className="text-textLight font-bold text-lg">−</Text>
              </Pressable>
              <Text className="text-textLight font-bold w-6 text-center">{item.quantity}</Text>
              <Pressable
                className="bg-accent1 w-8 h-8 rounded-full items-center justify-center"
                onPress={() => cart.setQuantity(item.menu_item_id, item.quantity + 1)}
              >
                <Text className="text-white font-bold text-lg">+</Text>
              </Pressable>
            </View>
            <Text className="text-textLight font-bold w-16 text-right">
              {(item.price * item.quantity).toFixed(2)} €
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <Text className="text-textMuted text-center mt-10">Košarica je prazna.</Text>
        }
      />

      {cart.items.length > 0 && (
        <View className="pb-8">
          <View className="flex-row justify-between py-4">
            <Text className="text-textMuted text-lg">Ukupno</Text>
            <Text className="text-textLight text-lg font-extrabold">{cart.total().toFixed(2)} €</Text>
          </View>
          <Text className="text-textMuted text-xs mb-3 text-center">
            VIP kupon (ako ga imaš) automatski se primjenjuje pri naplati.
            Kupon je vezan uz Vas osobno i ne može se dijeliti s drugim gostima.
          </Text>
          <Pressable
            className="bg-accent1 rounded-xl py-4 items-center"
            onPress={() => router.push('/order/checkout')}
          >
            <Text className="text-white font-bold text-base">Na naplatu</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}
