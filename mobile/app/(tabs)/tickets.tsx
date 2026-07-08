import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import FadeIn from '../../components/ui/FadeIn';
import PressableScale from '../../components/ui/PressableScale';
import ScreenHeader from '../../components/ui/ScreenHeader';
import { api } from '../../services/api';

const TICKET_STATUS: Record<string, { label: string; pill: string }> = {
  pending: { label: 'Čeka plaćanje', pill: 'text-warning bg-warning/10 border-warning/30' },
  valid: { label: 'Važeća', pill: 'text-success bg-success/10 border-success/30' },
  checked_in: { label: 'Iskorištena', pill: 'text-muted bg-white/5 border-line' },
  cancelled: { label: 'Otkazana', pill: 'text-error bg-error/10 border-error/30' },
};

const RES_STATUS: Record<string, { label: string; pill: string }> = {
  confirmed: { label: 'Potvrđena', pill: 'text-success bg-success/10 border-success/30' },
  checked_in: { label: 'Ušli ste', pill: 'text-success bg-success/10 border-success/30' },
  pending: { label: 'Čeka depozit', pill: 'text-warning bg-warning/10 border-warning/30' },
  cancelled: { label: 'Otkazana', pill: 'text-error bg-error/10 border-error/30' },
};

function Pill({ label, cls }: { label: string; cls: string }) {
  return (
    <View className={`px-3 py-1 rounded-full border ${cls}`}>
      <Text className={`font-bodySb text-[11px] ${cls.split(' ')[0]}`}>{label}</Text>
    </View>
  );
}

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
    <SafeAreaView edges={['top']} className="flex-1 bg-ink">
      <FlatList
        className="px-5"
        showsVerticalScrollIndicator={false}
        data={tickets}
        keyExtractor={(t) => t._id}
        ListHeaderComponent={<ScreenHeader eyebrow="Tvoja večer" title="Moje karte" />}
        renderItem={({ item, index }) => {
          const status = TICKET_STATUS[item.status] ?? { label: item.status, pill: 'text-muted bg-white/5 border-line' };
          return (
            <FadeIn delay={Math.min(index, 6) * 60}>
              <View className="bg-surface rounded-2xl p-5 mb-3 border border-line">
                <View className="flex-row items-start justify-between">
                  <Text className="text-white font-heading text-base uppercase flex-1 mr-3" style={{ letterSpacing: 0.3 }}>
                    {item.event?.name}
                  </Text>
                  <Pill label={status.label} cls={status.pill} />
                </View>
                <Text className="text-muted font-body mt-2">
                  {item.event?.date ? new Date(item.event.date).toLocaleString('hr-HR') : ''}
                  {'  ·  '}{item.ticket_type_name}{'  ·  '}{item.price_paid} €
                </Text>
                {item.status === 'valid' && (
                  <View className="items-center mt-4 bg-white rounded-2xl p-5">
                    <Text className="text-black font-body text-xs tracking-widest">{item.qr_code}</Text>
                    <Text className="text-black/50 font-body text-xs mt-1">Pokaži na ulazu</Text>
                  </View>
                )}
              </View>
            </FadeIn>
          );
        }}
        ListEmptyComponent={
          <Text className="text-muted font-body text-center mt-6">Još nemaš kupljenih karata.</Text>
        }
        ListFooterComponent={
          <View className="mb-10">
            <Text className="text-white font-display text-[26px] uppercase mt-8 mb-4" style={{ letterSpacing: 0.5 }}>
              Rezervacije
            </Text>
            {reservations.map((r, i) => {
              const st = RES_STATUS[r.status] ?? { label: r.status, pill: 'text-muted bg-white/5 border-line' };
              return (
                <FadeIn key={r._id} delay={Math.min(i, 5) * 60}>
                  <PressableScale
                    className="bg-surface rounded-2xl p-5 mb-3 border border-line"
                    onPress={() => router.push(`/reservation/confirm/${r._id}`)}
                  >
                    <View className="flex-row items-start justify-between">
                      <Text className="text-white font-heading text-base uppercase flex-1 mr-3" style={{ letterSpacing: 0.3 }}>
                        {r.event?.name}
                      </Text>
                      <Pill label={st.label} cls={st.pill} />
                    </View>
                    <Text className="text-muted font-body mt-2">
                      Stol {r.table_label}
                      {r.deposit_coupon_remaining > 0 ? `  ·  kupon: ${r.deposit_coupon_remaining} €` : ''}
                    </Text>
                  </PressableScale>
                </FadeIn>
              );
            })}
            {reservations.length === 0 && (
              <Text className="text-muted font-body text-center">Nemaš aktivnih rezervacija.</Text>
            )}
          </View>
        }
      />
    </SafeAreaView>
  );
}
