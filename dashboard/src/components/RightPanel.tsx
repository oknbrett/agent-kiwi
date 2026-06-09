import { DayData, DigestEntry, MEMORIES, MemoryEntry, getClientById } from '../data';
import { DECISION } from '../decision';
import { AlertTriangle, Brain, Clock, Lock } from './Icons';

interface Props {
  selectedClientId: string;
  day: DayData;
}

export default function RightPanel({ selectedClientId, day }: Props) {
  const client = getClientById(selectedClientId);
  const memory = MEMORIES[selectedClientId] ?? [];

  return (
    <aside className="scrollbar-thin flex w-[304px] shrink-0 flex-col overflow-y-auto bg-panel">
      <section>
        <header className="sticky top-0 z-10 border-b border-line bg-panel px-5 pb-2.5 pt-5">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-t3">
            Memory · <span className="text-t2">{client.name}</span>
          </h2>
        </header>

        <ul className="flex flex-col gap-2 px-4 py-3">
          {memory.length === 0 ? (
            <li className="px-1 text-[12px] text-t3">No entries yet.</li>
          ) : (
            memory.map((entry) => <MemoryChip key={entry.id} entry={entry} />)
          )}
        </ul>
      </section>

      <section className="mt-2">
        <header className="border-y border-line px-5 py-2.5">
          <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-t3">
            Coach digest · <span className="text-t2">{day.shortLabel}</span>
          </h2>
        </header>

        <ul className="flex flex-col gap-1.5 px-4 py-3 pb-6">
          {day.digest.map((entry) => (
            <DigestRow key={entry.clientId} entry={entry} />
          ))}
        </ul>
      </section>
    </aside>
  );
}

// ─── Memory chips ─────────────────────────────────────────────────────────────

const MEMORY_META = {
  profile: { Icon: Lock, label: 'Profile', tone: 'text-t2' },
  observation: { Icon: Brain, label: 'Observed', tone: 'text-t2' },
  escalation: { Icon: AlertTriangle, label: 'Escalation', tone: 'text-esc' },
  waiting: { Icon: Clock, label: 'Waiting', tone: 'text-mon' },
} as const;

function MemoryChip({ entry }: { entry: MemoryEntry }) {
  const meta = MEMORY_META[entry.type];
  const isEsc = entry.type === 'escalation';

  return (
    <li
      className={`rounded-lg border px-3.5 py-3 ${
        isEsc ? 'border-esc/30 bg-esc-dim/40' : 'border-line bg-card'
      }`}
    >
      <div className="mb-1 flex items-center gap-1.5">
        <meta.Icon size={11} className={meta.tone} />
        <span className={`font-mono text-[9.5px] uppercase tracking-[0.18em] ${meta.tone}`}>
          {meta.label}
        </span>
        <span className="ml-auto font-mono text-[10px] tabular-nums text-t3">
          {shortDate(entry.date)}
        </span>
      </div>

      <p className={`text-[12px] leading-relaxed ${isEsc ? 'text-esc/90' : 'text-t2'}`}>
        {entry.body}
      </p>

      {entry.confidence !== undefined && <ConfidenceMeter value={entry.confidence} />}
    </li>
  );
}

function ConfidenceMeter({ value }: { value: number }) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <div
        role="meter"
        aria-valuenow={Math.round(value * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="confidence"
        className="h-[3px] flex-1 overflow-hidden rounded-full bg-raise"
      >
        <div
          className="h-full rounded-full bg-kiwi/70 transition-[width] duration-300 ease-out"
          style={{ width: `${value * 100}%` }}
        />
      </div>
      <span className="font-mono text-[9.5px] tabular-nums text-t3">{value.toFixed(2)}</span>
    </div>
  );
}

// ─── Digest rows ──────────────────────────────────────────────────────────────

function DigestRow({ entry }: { entry: DigestEntry }) {
  const client = getClientById(entry.clientId);
  const d = DECISION[entry.decision];
  const isEsc = entry.decision === 'escalate';

  return (
    <li
      className={`rounded-lg px-3.5 py-2.5 ${
        isEsc ? 'border border-esc/30 bg-esc-dim/40' : 'border border-transparent'
      }`}
    >
      <div className="mb-0.5 flex items-center gap-2">
        <d.Icon size={12} className={d.color} />
        <span
          className={`font-display text-[12.5px] font-semibold ${isEsc ? 'text-esc' : 'text-t1'}`}
        >
          {client.name}
        </span>
      </div>
      <p className={`pl-[20px] text-[11.5px] leading-relaxed ${isEsc ? 'text-esc/85' : 'text-t3'}`}>
        {entry.text}
      </p>
    </li>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function shortDate(iso: string): string {
  const [, m, d] = iso.split('-');
  return `${MONTHS[parseInt(m, 10) - 1]} ${parseInt(d, 10)}`;
}
