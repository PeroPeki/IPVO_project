import { Pressable, Text, View } from 'react-native';

const STATUS_LABEL: Record<string, string> = {
  placed: 'Zaprimljena',
  accepted: 'Prihvaćena',
  preparing: 'U pripremi',
  delivered: 'Dostavljena',
  cancelled: 'Otkazana',
};

const STATUS_COLOR: Record<string, string> = {
  placed: 'text-warning',
  accepted: 'text-accent1',
  preparing: 'text-accent1',
  delivered: 'text-success',
  cancelled: 'text-error',
};

export default function OrderCard({
  order, actionLabel, onAction,
}: {
  order: any;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View className="bg-bgCard rounded-xl p-4 mb-3 border border-accent3">
      <View className="flex-row justify-between items-center">
        <Text className="text-textLight font-bold">Stol {order.table_label}</Text>
        <Text className={`font-semibold ${STATUS_COLOR[order.order_status] ?? 'text-textMuted'}`}>
          {STATUS_LABEL[order.order_status] ?? order.order_status}
        </Text>
      </View>
      {(order.items ?? []).map((i: any, idx: number) => (
        <Text key={idx} className="text-textMuted mt-1">
          {i.quantity}× {i.name}
        </Text>
      ))}
      <View className="flex-row justify-between items-center mt-3">
        <Text className="text-textMuted text-xs">
          {order.payment_method === 'cash' ? 'Gotovina' : 'Kartica'}
          {order.payment_status === 'paid' ? ' · plaćeno' : ''}
          {order.coupon_applied ? ` · kupon −${order.coupon_applied} €` : ''}
        </Text>
        <Text className="text-textLight font-bold">{order.total} €</Text>
      </View>
      {actionLabel && onAction && (
        <Pressable className="bg-accent1 rounded-lg py-3 items-center mt-3" onPress={onAction}>
          <Text className="text-white font-bold">{actionLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}
