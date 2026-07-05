import { useState } from 'react';
import { ActivityIndicator, Pressable, Text } from 'react-native';
import { Colors } from '../constants/colors';
import { payWithSheet } from '../services/stripe';

/**
 * Gumb koji otvara Stripe Payment Sheet (kartice, Apple Pay, Google Pay).
 */
export default function PaymentSheet({
  clientSecret, label, onSuccess, onError,
}: {
  clientSecret: string;
  label: string;
  onSuccess: () => void;
  onError: (message: string) => void;
}) {
  const [loading, setLoading] = useState(false);

  async function pay() {
    setLoading(true);
    try {
      const result = await payWithSheet(clientSecret);
      if (result.ok) onSuccess();
      else if (result.error) onError(result.error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Pressable
      className="bg-accent1 rounded-xl py-4 items-center"
      onPress={pay}
      disabled={loading}
    >
      {loading
        ? <ActivityIndicator color={Colors.white} />
        : <Text className="text-white font-bold text-base">{label}</Text>}
    </Pressable>
  );
}
