import { useEffect } from 'react';
import { getSocket } from '../services/socket';

/** Pretplata na Socket.IO event uz automatski cleanup. */
export function useSocketEvent(event: string, handler: (data: any) => void) {
  useEffect(() => {
    const socket = getSocket();
    socket.on(event, handler);
    return () => {
      socket.off(event, handler);
    };
  }, [event, handler]);
}
