import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Easing, ViewProps } from 'react-native';

/**
 * Mount fade + blagi rise. Suzdržana animacija koja se koristi za listanje
 * ekrana i kartica (uz mali `delay` za stagger). Poštuje "reduce motion".
 */
export default function FadeIn({
  delay = 0,
  offset = 14,
  duration = 420,
  style,
  children,
  ...rest
}: ViewProps & { delay?: number; offset?: number; duration?: number }) {
  const [reduced, setReduced] = useState(false);
  const p = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    let active = true;
    AccessibilityInfo.isReduceMotionEnabled().then((v) => {
      if (!active) return;
      if (v) {
        setReduced(true);
        p.setValue(1);
      } else {
        Animated.timing(p, {
          toValue: 1,
          duration,
          delay,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }).start();
      }
    });
    return () => { active = false; };
  }, []);

  return (
    <Animated.View
      style={[
        {
          opacity: p,
          transform: reduced
            ? []
            : [{ translateY: p.interpolate({ inputRange: [0, 1], outputRange: [offset, 0] }) }],
        },
        style,
      ]}
      {...rest}
    >
      {children}
    </Animated.View>
  );
}
