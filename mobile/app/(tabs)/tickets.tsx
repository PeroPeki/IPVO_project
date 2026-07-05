import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';
import { api } from '../../services/api';

const TICKET_STATUS: Record<string, { label: string; cls: string }> = {
  pending: { label: 'Čeka plaćanje', cls: 'text-warning' },
  valid: { label: 'Važeća', cls: 'text-success' },
  checked_in: { label: 'Iskorištena', cls: 'text-textMuted' },
  cancelled: { label: 'Otkazana', cls: 'text-error' },
};

/** Moje karte i rezervacije. */
export default function Tickets() {
  const router = useRouter();
  const [tickets, setTickets] = useState<any[]>([]);
  const [reservations, setReservations] = useState<any[]>([]);

  useFocusEffect(
    useCallback(() => {
      api.get('/api/tickets/my').then((r) => setTickets(r.data.tickets)).catch(() => {});
      api.get('/api/reservations/my').then((r) => setReservations(r.data.reservations)).catch(() => {});
    }, []),
  );

  return (
    <FlatList
      className="flex-1 bg-bgDark px-4"
      data={tickets}
      keyExtractor={(t) => t._id}
      ListHeaderComponent={
        <Text className="text-textLight text-2xl font-extrabold mt-4 mb-3">Moje karte</Text>
      }
      renderItem={({ item }) => {
        const status = TICKET_STATUS[item.status] ?? { label: item.status, cls: 'text-textMuted' };
        return (
          <View className="bg-bgCard rounded-xl p-4 mb-3 border border-accent3">
            <View className="flex-row justify-between">
              <Text className="text-textLight font-bold flex-1">{item.event?.name}</Text>
              <Text className={`font-semibold ${status.cls}`}>{status.label}</Text>
            </View>
            <Text className="text-textMuted mt-1">
              {item.event?.date ? new Date(item.event.date).toLocaleString('hr-HR') : ''}
              {' · '}{item.ticket_type_name} · {item.price_paid} €
            </Text>
            {item.status === 'valid' && (
              <View className="items-center mt-3 bg-white rounded-xl p-4">
                {/* QR kod = UUID; hostesa skenira ili upisuje */}
                <Text className="text-black font-mono text-xs">{item.qr_code}</Text>
                <Text className="text-black/50 text-xs mt-1">Pokaži na ulazu</Text>
              </View>
            )}
          </View>
        );
      }}
      ListEmptyComponent={
        <Text className="text-textMuted text-center mt-6">Još nemaš kupljenih karata.</Text>
      }
      ListFooterComponent={
        <View className="mb-8">
          <Text className="text-textLight text-2xl font-extrabold mt-6 mb-3">Moje rezervacije</Text>
          {reservations.map((r) => (
            <Pressable
              key={r._id}
              className="bg-bgCard rounded-xl p-4 mb-3 border border-accent3"
              onPress={() => router.push(`/reservation/confirm/${r._id}`)}
            >
              <View className="flex-row justify-between">
                <Text className="text-textLight font-bold flex-1">{r.event?.name}</Text>
                <Text className={`font-semibold ${
                  r.status === 'confirmed' || r.status === 'checked_in' ? 'text-success'
                    : r.status === 'pending' ? 'text-warning' : 'text-error'
                }`}>
                  {r.status === 'confirmed' ? 'Potvrđena'
                    : r.status === 'pending' ? 'Čeka depozit'
                    : r.status === 'checked_in' ? 'Ušli ste' : 'Otkazana'}
                </Text>
              </View>
              <Text className="text-textMuted mt-1">
                Stol {r.table_label}
                {r.deposit_coupon_remaining > 0 ? ` · kupon: ${r.deposit_coupon_remaining} €` : ''}
              </Text>
            </Pressable>
          ))}
          {reservations.length === 0 && (
            <Text className="text-textMuted text-center">Nemaš aktivnih rezervacija.</Text>
          )}
        </View>
      }
    />
  );
}
