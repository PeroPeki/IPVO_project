import { useState } from 'react';
import { ActivityIndicator, Text } from 'react-native';
import { glow } from '../constants/theme';
import { payWithSheet } from '../services/stripe';
import PressableScale from './ui/PressableScale';

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
    <PressableScale
      className="bg-neon rounded-2xl py-4 items-center"
      style={glow}
      onPress={pay}
      disabled={loading}
    >
      {loading
        ? <ActivityIndicator color="#FFFFFF" />
        : <Text className="text-white font-bodyBd text-base">{label}</Text>}
    </PressableScale>
  );
}
