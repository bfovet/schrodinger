import type { EventData } from '../types/event';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchEvents(name?: string): Promise<EventData[]> {
  const url = new URL(`${API_BASE}/api/v1/events/`);
  if (name) url.searchParams.set('name', name);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch events');
  return res.json();
}

export async function fetchEvent(id: string): Promise<EventData> {
  const res = await fetch(`${API_BASE}/api/v1/events/${id}`);
  if (!res.ok) throw new Error('Failed to fetch event');
  return res.json();
}

export function getImageUrl(s3Key: string): string {
  return `${API_BASE}/api/v1/files/${s3Key}`;
}