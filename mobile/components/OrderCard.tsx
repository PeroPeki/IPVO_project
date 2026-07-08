import { Text, View } from 'react-native';
import PressableScale from './ui/PressableScale';

const STATUS_LABEL: Record<string, string> = {
  placed: 'Zaprimljena',
  accepted: 'Prihvaćena',
  preparing: 'U pripremi',
  delivered: 'Dostavljena',
  cancelled: 'Otkazana',
};

const STATUS_COLOR: Record<string, string> = {
  placed: 'text-warning',
  accepted: 'text-neon',
  preparing: 'text-neon',
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
    <View className="bg-surface rounded-2xl p-4 mb-3 border border-line">
      <View className="flex-row justify-between items-center">
        <Text className="text-white font-heading uppercase" style={{ letterSpacing: 0.3 }}>Stol {order.table_label}</Text>
        <Text className={`font-bodySb text-xs ${STATUS_COLOR[order.order_status] ?? 'text-muted'}`}>
          {STATUS_LABEL[order.order_status] ?? order.order_status}
        </Text>
      </View>
      {(order.items ?? []).map((i: any, idx: number) => (
        <Text key={idx} className="text-muted font-body mt-1">
          {i.quantity}× {i.name}
        </Text>
      ))}
      <View className="flex-row justify-between items-center mt-3">
        <Text className="text-muted font-body text-xs">
          {order.payment_method === 'cash' ? 'Gotovina' : 'Kartica'}
          {order.payment_status === 'paid' ? ' · plaćeno' : ''}
          {order.coupon_applied ? ` · kupon −${order.coupon_applied} €` : ''}
        </Text>
        <Text className="text-white font-heading">{order.total} €</Text>
      </View>
      {actionLabel && onAction && (
        <PressableScale className="bg-neon rounded-xl py-3 items-center mt-3" onPress={onAction}>
          <Text className="text-white font-bodyBd">{actionLabel}</Text>
        </PressableScale>
      )}
    </View>
  );
}
