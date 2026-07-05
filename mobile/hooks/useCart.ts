import { useCartStore } from '../store';

export function useCart() {
  return useCartStore();
}
