import { Text, View } from 'react-native';
import { useCart } from '../hooks/useCart';
import PressableScale from './ui/PressableScale';

export default function MenuCategory({ category }: { category: any }) {
  const cart = useCart();

  return (
    <View className="mb-7">
      <Text className="text-neon font-sub text-base uppercase mb-3" style={{ letterSpacing: 1 }}>{category.name}</Text>
      {category.items.map((item: any) => {
        const inCart = cart.items.find((i) => i.menu_item_id === item.id);
        const available = item.is_available !== false;
        return (
          <View
            key={item.id}
            className={`bg-surface rounded-2xl p-4 mb-2.5 flex-row items-center border border-line ${available ? '' : 'opacity-40'}`}
          >
            <View className="flex-1">
              <Text className="text-white font-bodySb">{item.name}</Text>
              <Text className="text-muted font-body text-xs mt-0.5">
                {item.volume ? `${item.volume} · ` : ''}{item.price} €
                {!available ? ' · nedostupno' : ''}
              </Text>
            </View>
            {available && (
              inCart ? (
                <View className="flex-row items-center gap-3">
                  <PressableScale
                    className="bg-surfaceHi w-9 h-9 rounded-full items-center justify-center border border-line"
                    onPress={() => cart.setQuantity(item.id, inCart.quantity - 1)}
                  >
                    <Text className="text-white font-bodyBd text-lg">−</Text>
                  </PressableScale>
                  <Text className="text-white font-heading w-5 text-center">{inCart.quantity}</Text>
                  <PressableScale
                    className="bg-neon w-9 h-9 rounded-full items-center justify-center"
                    onPress={() => cart.add({ menu_item_id: item.id, name: item.name, price: item.price })}
                  >
                    <Text className="text-white font-bodyBd text-lg">+</Text>
                  </PressableScale>
                </View>
              ) : (
                <PressableScale
                  className="bg-neon px-5 py-2 rounded-full"
                  onPress={() => cart.add({ menu_item_id: item.id, name: item.name, price: item.price })}
                >
                  <Text className="text-white font-bodyBd">Dodaj</Text>
                </PressableScale>
              )
            )}
          </View>
        );
      })}
    </View>
  );
}
