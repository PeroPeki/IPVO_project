import { Pressable, Text, View } from 'react-native';
import { useCart } from '../hooks/useCart';

export default function MenuCategory({ category }: { category: any }) {
  const cart = useCart();

  return (
    <View className="mb-6">
      <Text className="text-accent1 font-bold text-base uppercase mb-2">{category.name}</Text>
      {category.items.map((item: any) => {
        const inCart = cart.items.find((i) => i.menu_item_id === item.id);
        const available = item.is_available !== false;
        return (
          <View
            key={item.id}
            className={`bg-bgCard rounded-xl p-4 mb-2 flex-row items-center border border-accent3 ${available ? '' : 'opacity-40'}`}
          >
            <View className="flex-1">
              <Text className="text-textLight font-semibold">{item.name}</Text>
              <Text className="text-textMuted text-xs mt-0.5">
                {item.volume ? `${item.volume} · ` : ''}{item.price} €
                {!available ? ' · nedostupno' : ''}
              </Text>
            </View>
            {available && (
              inCart ? (
                <View className="flex-row items-center gap-3">
                  <Pressable
                    className="bg-accent3 w-8 h-8 rounded-full items-center justify-center"
                    onPress={() => cart.setQuantity(item.id, inCart.quantity - 1)}
                  >
                    <Text className="text-textLight font-bold text-lg">−</Text>
                  </Pressable>
                  <Text className="text-textLight font-bold">{inCart.quantity}</Text>
                  <Pressable
                    className="bg-accent1 w-8 h-8 rounded-full items-center justify-center"
                    onPress={() => cart.add({ menu_item_id: item.id, name: item.name, price: item.price })}
                  >
                    <Text className="text-white font-bold text-lg">+</Text>
                  </Pressable>
                </View>
              ) : (
                <Pressable
                  className="bg-accent1 px-4 py-2 rounded-full"
                  onPress={() => cart.add({ menu_item_id: item.id, name: item.name, price: item.price })}
                >
                  <Text className="text-white font-bold">Dodaj</Text>
                </Pressable>
              )
            )}
          </View>
        );
      })}
    </View>
  );
}
