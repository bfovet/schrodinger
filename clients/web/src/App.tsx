import { useState } from 'react';
import { Timeline } from './components/Timeline';
import { EventDetail } from './components/EventDetail';
import type { EventData } from './types/event';
import './App.css';

function App() {
  const [selectedEvent, setSelectedEvent] = useState<EventData | null>(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Event Timeline</h1>
      </header>
      <main>
        <Timeline onEventClick={setSelectedEvent} />
      </main>
      {selectedEvent && (
        <EventDetail
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  );
}

export default App;
