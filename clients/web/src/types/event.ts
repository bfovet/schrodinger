export type EventData = {
  id: string;
  entity_id: number;
  name: string;
  event_type: string;
  timestamp: string;
  raw_frame_s3_key: string;
  annotated_frame_s3_key: string;
}