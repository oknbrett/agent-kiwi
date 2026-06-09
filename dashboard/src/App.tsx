import { useState } from 'react';
import { DAYS, CLIENTS } from './data';
import ClientSidebar from './components/ClientSidebar';
import WeekTimeline from './components/WeekTimeline';
import DayFeed from './components/DayFeed';
import RightPanel from './components/RightPanel';
import { KiwiMark, ExternalLink } from './components/Icons';

// Default to Friday — the escalation day — so the story lands immediately.
const DEFAULT_DAY = '2026-06-05';
const DEFAULT_CLIENT = 'sofia';

export default function App() {
  const [selectedDay, setSelectedDay] = useState(DEFAULT_DAY);
  const [selectedClient, setSelectedClient] = useState(DEFAULT_CLIENT);

  const day = DAYS.find((d) => d.date === selectedDay)!;

  return (
    <div className="flex h-full flex-col bg-ink text-t1">
      <header className="flex shrink-0 items-center justify-between border-b border-line px-6 py-3">
        <div className="flex items-baseline gap-3">
          <span className="flex items-center gap-2.5">
            <KiwiMark size={22} />
            <span className="font-display text-[15px] font-bold tracking-[0.18em] text-t1">
              KIWI
            </span>
          </span>
          <span className="font-mono text-[11px] tracking-wide text-t3">coach console</span>
        </div>
        <div className="flex items-center gap-5">
          <span className="font-mono text-[11px] text-t3">
            {CLIENTS.length} clients · Jun 1–5 2026
          </span>
          <a
            href="https://github.com/oknbrett/agent-kiwi"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 font-mono text-[11px] text-t2 transition-colors duration-200 hover:text-kiwi"
          >
            oknbrett/agent-kiwi
            <ExternalLink size={11} />
          </a>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <ClientSidebar
          clients={CLIENTS}
          selectedClientId={selectedClient}
          selectedDay={day}
          onSelect={setSelectedClient}
        />

        <main className="flex min-w-0 flex-1 flex-col border-r border-line">
          <WeekTimeline days={DAYS} selectedDate={selectedDay} onSelect={setSelectedDay} />
          <DayFeed day={day} selectedClientId={selectedClient} onClientSelect={setSelectedClient} />
        </main>

        <RightPanel selectedClientId={selectedClient} day={day} />
      </div>
    </div>
  );
}
