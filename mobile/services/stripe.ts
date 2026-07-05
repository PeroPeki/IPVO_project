/**
 * Stripe helper — inicijalizacija i prikaz Payment Sheeta.
 * Apple Pay / Google Pay rade automatski kroz initPaymentSheet.
 */

import { initPaymentSheet, presentPaymentSheet } from '@stripe/stripe-react-native';

export async function payWithSheet(clientSecret: string): Promise<{ ok: boolean; error?: string }> {
  const init = await initPaymentSheet({
    merchantDisplayName: 'NightClub Manager',
    paymentIntentClientSecret: clientSecret,
    style: 'alwaysDark',
    applePay: { merchantCountryCode: 'HR' },
    googlePay: { merchantCountryCode: 'HR', currencyCode: 'EUR', testEnv: true },
  });
  if (init.error) return { ok: false, error: init.error.message };

  const result = await presentPaymentSheet();
  if (result.error) {
    if (result.error.code === 'Canceled') return { ok: false };
    return { ok: false, error: result.error.message };
  }
  return { ok: true };
}
