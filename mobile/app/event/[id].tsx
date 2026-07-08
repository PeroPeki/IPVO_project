import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, Text, View } from 'react-native';
import PaymentSheet from '../../components/PaymentSheet';
import PressableScale from '../../components/ui/PressableScale';
import { glow, scrim } from '../../constants/theme';
import { api, errorMessage } from '../../services/api';

/** Detalji eventa: lineup, tipovi karata (kupnja), ulaz u rezervaciju stola. */
export default function EventDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<any>(null);
  const [purchase, setPurchase] = useState<{ clientSecret: string; ticketId: string } | null>(null);
  const [buying, setBuying] = useState<string | null>(null);

  function load() {
    api.get(`/api/events/${id}`).then((res) => setEvent(res.data)).catch(() => {});
  }

  useEffect(load, [id]);

  async function buyTicket(ticketTypeId: string) {
    setBuying(ticketTypeId);
    try {
      const res = await api.post('/api/tickets/purchase', { event_id: id, ticket_type_id: ticketTypeId });
      setPurchase({ clientSecret: res.data.client_secret, ticketId: res.data.ticket_id });
    } catch (err: any) {
      Alert.alert('Kupnja nije moguća', errorMessage(err));
    } finally {
      setBuying(null);
    }
  }

  if (!event) return <View className="flex-1 bg-ink" />;

  const date = new Date(event.date);

  return (
    <ScrollView className="flex-1 bg-ink" showsVerticalScrollIndicator={false}>
      {/* Hero */}
      <View className="h-[400px] justify-end">
        {event.cover_image ? (
          <Image source={{ uri: event.cover_image }} style={StyleSheet.absoluteFill} resizeMode="cover" />
        ) : (
          <View style={StyleSheet.absoluteFill} className="bg-surfaceHi" />
        )}
        <LinearGradient colors={scrim as any} style={StyleSheet.absoluteFill} />
        <View className="px-5 pb-6">
          <Text className="text-neon font-bodySb text-xs uppercase" style={{ letterSpacing: 2 }}>
            {date.toLocaleDateString('hr-HR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          </Text>
          <Text className="text-white font-display text-[36px] leading-[40px] uppercase mt-2" style={{ letterSpacing: 0.4 }}>
            {event.name}
          </Text>
          <Text className="text-muted font-body mt-2">
            {event.club?.name}  ·  {event.club?.location?.city}
            {event.doors_open ? `  ·  vrata ${event.doors_open}` : ''}
          </Text>
        </View>
      </View>

      <View className="px-5 pt-6 pb-14">
        {event.description ? (
          <Text className="text-text font-body leading-6 mb-2">{event.description}</Text>
        ) : null}

        {(event.lineup ?? []).length > 0 && (
          <>
            <Text className="text-white font-display text-[22px] uppercase mt-7 mb-3" style={{ letterSpacing: 0.5 }}>Lineup</Text>
            {event.lineup.map((a: any, i: number) => (
              <View key={i} className="flex-row justify-between items-center bg-surface rounded-2xl px-4 py-3.5 mb-2 border border-line">
                <Text className="text-white font-bodySb">{a.artist_name}</Text>
                {a.stage_time ? <Text className="text-muted font-body">{a.stage_time}</Text> : null}
              </View>
            ))}
          </>
        )}

        <Text className="text-white font-display text-[22px] uppercase mt-7 mb-3" style={{ letterSpacing: 0.5 }}>Ulaznice</Text>
        {(event.ticket_types ?? []).filter((t: any) => t.is_active !== false).map((t: any) => {
          const soldOut = t.sold_quantity >= t.total_quantity;
          return (
            <View key={t.id} className="bg-surface rounded-2xl p-4 mb-2.5 border border-line flex-row items-center">
              <View className="flex-1">
                <Text className="text-white font-bodySb text-base">{t.name}</Text>
                <Text className={`font-body text-xs mt-1 ${soldOut ? 'text-error' : 'text-muted'}`}>
                  {soldOut ? 'Rasprodano' : `${t.total_quantity - t.sold_quantity} preostalo`}
                </Text>
              </View>
              <Text className="text-white font-heading text-base mr-4">{t.price} €</Text>
              <PressableScale
                className={`px-5 py-2.5 rounded-full ${soldOut ? 'bg-surfaceHi' : 'bg-neon'}`}
                style={soldOut ? undefined : glow}
                disabled={soldOut || buying === t.id}
                onPress={() => buyTicket(t.id)}
              >
                <Text className={`font-bodyBd ${soldOut ? 'text-muted' : 'text-white'}`}>
                  {buying === t.id ? '…' : soldOut ? '—' : 'Kupi'}
                </Text>
              </PressableScale>
            </View>
          );
        })}

        {purchase && (
          <View className="mt-3">
            <PaymentSheet
              clientSecret={purchase.clientSecret}
              label="Plati karticom / Apple Pay / Google Pay"
              onSuccess={() => {
                setPurchase(null);
                Alert.alert('Uspjeh', 'Karta je kupljena! Nalazi se pod „Moje karte".');
                const pi = purchase.clientSecret.split('_secret')[0];
                api.post('/api/tickets/confirm', { payment_intent_id: pi }).catch(() => {});
                load();
              }}
              onError={(msg) => Alert.alert('Plaćanje nije uspjelo', msg)}
            />
          </View>
        )}

        <PressableScale
          className="border border-neon/60 bg-neon/10 rounded-2xl py-4 items-center mt-7"
          onPress={() => router.push(`/reservation/map/${id}`)}
        >
          <Text className="text-white font-bodyBd text-base">Rezerviraj stol</Text>
        </PressableScale>

        {(event.age_limit || event.dress_code) && (
          <Text className="text-muted font-body text-xs mt-5 text-center">
            {event.age_limit ? `${event.age_limit}+` : ''}
            {event.age_limit && event.dress_code ? '  ·  ' : ''}
            {event.dress_code ?? ''}
          </Text>
        )}
      </View>
    </ScrollView>
  );
}
