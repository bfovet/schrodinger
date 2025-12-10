import { useState } from 'react';
import type { EventData } from '../types/event';
import { getImageUrl } from '../api/events';
import './EventDetail.css';

interface EventDetailProps {
  event: EventData;
  onClose: () => void;
}

export function EventDetail({ event, onClose }: EventDetailProps) {
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  return (
    <>
      <div className="event-detail-overlay" onClick={onClose}>
        <div className="event-detail-modal" onClick={(e) => e.stopPropagation()}>
          <button className="event-detail-close" onClick={onClose}>
            ×
          </button>
          <h2>{event.name}</h2>
          <div className="event-detail-info">
            <p><strong>Time:</strong> {new Date(event.timestamp).toLocaleString()}</p>
            <p><strong>Type:</strong> {event.event_type}</p>
            <p><strong>Entity ID:</strong> {event.entity_id}</p>
          </div>
          <div className="event-detail-images">
            <div className="event-detail-image-container">
              <h3>Raw Frame</h3>
              <img
                src={getImageUrl(event.raw_frame_s3_key)}
                alt="Raw frame"
                onClick={() => setLightboxImage(getImageUrl(event.raw_frame_s3_key))}
              />
            </div>
            <div className="event-detail-image-container">
              <h3>Annotated Frame</h3>
              <img
                src={getImageUrl(event.annotated_frame_s3_key)}
                alt="Annotated frame"
                onClick={() => setLightboxImage(getImageUrl(event.annotated_frame_s3_key))}
              />
            </div>
          </div>
        </div>
      </div>
      {lightboxImage && (
        <div className="lightbox-overlay" onClick={() => setLightboxImage(null)}>
          <img src={lightboxImage} alt="Full size" className="lightbox-image" />
        </div>
      )}
    </>
  );
}