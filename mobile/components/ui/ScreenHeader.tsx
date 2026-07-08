import { ReactNode } from 'react';
import { Text, View } from 'react-native';

/**
 * Editorial zaglavlje ekrana: mali neon "eyebrow" + veliki uppercase Syne
 * naslov. `topInset` ubacuje safe-area razmak kad ekran nema navigacijski header.
 */
export default function ScreenHeader({
  eyebrow,
  title,
  subtitle,
  right,
  topInset = 0,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  right?: ReactNode;
  topInset?: number;
}) {
  return (
    <View style={{ paddingTop: topInset + 8 }} className="pb-5">
      <View className="flex-row items-end justify-between">
        <View className="flex-1">
          {eyebrow ? (
            <Text className="text-neon font-bodySb text-[11px] uppercase mb-2" style={{ letterSpacing: 3 }}>
              {eyebrow}
            </Text>
          ) : null}
          <Text className="text-white font-display text-[34px] leading-[38px] uppercase" style={{ letterSpacing: 0.5 }}>
            {title}
          </Text>
          {subtitle ? <Text className="text-muted font-body mt-2">{subtitle}</Text> : null}
        </View>
        {right ? <View className="ml-3">{right}</View> : null}
      </View>
    </View>
  );
}
