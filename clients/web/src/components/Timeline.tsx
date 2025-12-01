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

  if (loading) return <div className="timeline-loading">Loading events...</div>;
  if (error) return <div className="timeline-error">{error}</div>;

  return (
    <div className="timeline">
      {events.map((event) => (
        <div
          key={event.id}
          className="timeline-event"
          onClick={() => onEventClick(event)}
        >
          <div className="timeline-card">
            <div className="timeline-card-header">
              <div className="timeline-avatar">🐱</div>
              <div className="timeline-meta">
                <div className="timeline-name">{event.name} {event.event_type}</div>
                <div className="timeline-time">
                  {new Date(event.timestamp).toLocaleString()}
                </div>
              </div>
            </div>
            <div className="timeline-thumbnail-wrapper">
              <img
                className="timeline-thumbnail"
                src={getImageUrl(event.annotated_frame_s3_key)}
                alt={`${event.name} ${event.event_type}`}
              />
              <div className="timeline-status">detected</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}