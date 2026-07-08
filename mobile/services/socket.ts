/** Socket.IO konfiguracija — jedna dijeljena konekcija na backend. */

import { io, Socket } from 'socket.io-client';
import { API_URL, getAccessToken } from './api';

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(API_URL, {
      transports: ['websocket'],
      // Backend odbija konekcije bez važećeg JWT-a; callback oblik
      // osigurava svjež token i kod reconnecta
      auth: (cb) => {
        getAccessToken().then((token) => cb({ token }));
      },
    });
  }
  return socket;
}

/** Prekida konekciju (npr. kod logouta) — sljedeći getSocket() se spaja iznova. */
export function resetSocket() {
  socket?.disconnect();
  socket = null;
}

export function joinEventRoom(eventId: string) {
  getSocket().emit('join_event', { event_id: eventId });
}

export function leaveEventRoom(eventId: string) {
  getSocket().emit('leave_event', { event_id: eventId });
}

export function joinBarRoom(eventId: string) {
  getSocket().emit('join_bar', { event_id: eventId });
}
