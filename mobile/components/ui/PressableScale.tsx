import { cssInterop } from 'nativewind';
import { useRef } from 'react';
import { Animated, Pressable, PressableProps, ViewStyle } from 'react-native';

// NativeWind v4 ne interopira Animated.View po defaultu — omogući `className` na njemu.
cssInterop(Animated.View, { className: 'style' });

/**
 * Pressable s blagim spring scale feedbackom. `className` i `style` idu na
 * unutarnji Animated.View pa se ponaša kao obična stilizirana ploha.
 */
export default function PressableScale({
  className,
  style,
  children,
  onPressIn,
  onPressOut,
  ...rest
}: PressableProps & { className?: string; style?: ViewStyle | ViewStyle[] }) {
  const s = useRef(new Animated.Value(1)).current;
  const to = (v: number) =>
    Animated.spring(s, { toValue: v, useNativeDriver: true, speed: 40, bounciness: 0 }).start();

  return (
    <Pressable
      onPressIn={(e) => { to(0.97); onPressIn?.(e); }}
      onPressOut={(e) => { to(1); onPressOut?.(e); }}
      {...rest}
    >
      <Animated.View className={className} style={[style as any, { transform: [{ scale: s }] }]}>
        {children as any}
      </Animated.View>
    </Pressable>
  );
}
