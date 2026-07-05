/** Socket.IO konfiguracija — jedna dijeljena konekcija na backend. */

import { io, Socket } from 'socket.io-client';
import { API_URL } from './api';

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(API_URL, { transports: ['websocket'] });
  }
  return socket;
}

export function joinEventRoom(eventId: string) {
  getSocket().emit('join_event', { event_id: eventId });
}

export function leaveEventRoom(eventId: string) {
  getSocket().emit('leave_event', { event_id: eventId });
}

export function joinWaiterRoom(waiterId: string) {
  getSocket().emit('join_waiter', { waiter_id: waiterId });
}

export function joinBarRoom(eventId: string) {
  getSocket().emit('join_bar', { event_id: eventId });
}
