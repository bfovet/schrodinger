import { useEffect, useState } from 'react';
import type { EventData } from '../types/event';
import { fetchEvents, getImageUrl } from '../api/events';
import './Timeline.css';

interface TimelineProps {
  onEventClick: (event: EventData) => void;
}

export function Timeline({ onEventClick }: TimelineProps) {
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEvents()
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="timeline-loading">Loading...</div>;
  if (error) return <div className="timeline-error">{error}</div>;

  return (
    <div className="timeline">
      {events.map((event) => (
        <div
          key={event.id}
          className="timeline-event"
          onClick={() => onEventClick(event)}
        >
          <img
            className="timeline-thumbnail"
            src={getImageUrl(event.annotated_frame_s3_key)}
            alt={`${event.name} ${event.event_type}`}
          />
          <div className="timeline-info">
            <div className="timeline-name">{event.name} {event.event_type}</div>
            <div className="timeline-time">
              {new Date(event.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}