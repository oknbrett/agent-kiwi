import { DayData, Decision, ObsEntry, getClientById } from '../data';
import { DECISION } from '../decision';
import { ArrowRight, MessageSquare, MoonStar } from './Icons';

interface Props {
  day: DayData;
  selectedClientId: string;
  onClientSelect: (id: string) => void;
}

const ORDER: Decision[] = ['escalate', 'monitor', 'none', 'quiet'];

export default function DayFeed({ day, selectedClientId, onClientSelect }: Props) {
  const entries = [...day.entries].sort(
    (a, b) => ORDER.indexOf(a.triage.decision) - ORDER.indexOf(b.triage.decision),
  );
  const quiet = day.digest.filter(
    (d) => d.decision === 'quiet' && !day.entries.some((e) => e.clientId === d.clientId),
  );

  return (
    <div className="scrollbar-thin flex-1 overflow-y-auto px-8 py-6">
      <div className="mx-auto max-w-[620px]">
        <div className="mb-5 flex items-baseline justify-between">
          <h1 className="font-display text-[20px] font-semibold tracking-tight text-t1">
            {day.label}
          </h1>
          <span className="font-mono text-[11px] tabular-nums text-t3">
            {entries.length} signals · {quiet.length} quiet
          </span>
        </div>

        {/* The log: a spine on the left, entries hanging off it */}
        <ol className="relative flex flex-col gap-4 before:absolute before:bottom-2 before:left-[15px] before:top-2 before:w-px before:bg-line">
          {entries.map((entry) => (
            <li key={entry.clientId} className="relative pl-11">
              <SpineNode decision={entry.triage.decision} />
              {entry.triage.decision === 'escalate' ? (
                <EscalationCard
                  entry={entry}
                  isSelected={entry.clientId === selectedClientId}
                  onClick={() => onClientSelect(entry.clientId)}
                />
              ) : (
                <SignalCard
                  entry={entry}
                  isSelected={entry.clientId === selectedClientId}
                  onClick={() => onClientSelect(entry.clientId)}
                />
              )}
            </li>
          ))}

          {quiet.map((q) => {
            const client = getClientById(q.clientId);
            const isSelected = q.clientId === selectedClientId;
            return (
              <li key={q.clientId} className="relative pl-11">
                <SpineNode decision="quiet" />
                <button
                  onClick={() => onClientSelect(q.clientId)}
                  className={`flex w-full items-center gap-2.5 rounded-lg border border-line/60 px-4 py-3 transition-colors duration-200 ${
                    isSelected ? 'bg-card' : 'hover:bg-card/60'
                  }`}
                >
                  <MoonStar size={13} className="shrink-0 text-qt" />
                  <span className="text-[12.5px] text-t3">
                    <span className="font-display font-medium text-t2">{client.name}</span>
                    {'  '}
                    {q.text}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

function SpineNode({ decision }: { decision: Decision }) {
  const d = DECISION[decision];
  return (
    <span
      className={`absolute left-0 top-4 flex h-[31px] w-[31px] items-center justify-center rounded-full border border-line bg-ink ${d.color}`}
    >
      <d.Icon size={14} />
    </span>
  );
}

// ─── Routine signal ───────────────────────────────────────────────────────────

function SignalCard({
  entry,
  isSelected,
  onClick,
}: {
  entry: ObsEntry;
  isSelected: boolean;
  onClick: () => void;
}) {
  const client = getClientById(entry.clientId);
  const d = DECISION[entry.triage.decision];

  return (
    <button
      onClick={onClick}
      className={`rise-in block w-full rounded-lg border px-4 py-3.5 transition-colors duration-200 ${
        isSelected ? 'border-line-2 bg-card' : 'border-line bg-panel hover:bg-card'
      }`}
    >
      <div className="mb-1.5 flex items-baseline gap-2.5">
        <span className="font-display text-[13.5px] font-semibold text-t1">{client.name}</span>
        <span className="text-[11px] text-t3">{client.goal}</span>
        <span
          className={`ml-auto rounded px-1.5 py-px font-mono text-[10px] uppercase tracking-wider ${d.color} ${d.dim}`}
        >
          {d.label}
        </span>
      </div>

      <p className="mb-1.5 text-[13px] leading-relaxed text-t2">“{entry.text}”</p>
      <p className={`text-[11.5px] leading-relaxed ${d.color} opacity-85`}>
        {entry.triage.reason}
      </p>

      <div className="mt-3 flex gap-2 border-t border-line/70 pt-2.5">
        <MessageSquare size={12} className="mt-0.5 shrink-0 text-t3" />
        <p className="text-[12px] leading-relaxed text-t3">{entry.checkin}</p>
      </div>
    </button>
  );
}

// ─── The escalation — the day's centrepiece ───────────────────────────────────

function EscalationCard({
  entry,
  isSelected,
  onClick,
}: {
  entry: ObsEntry;
  isSelected: boolean;
  onClick: () => void;
}) {
  const client = getClientById(entry.clientId);

  return (
    <button
      onClick={onClick}
      aria-pressed={isSelected}
      className="rise-in esc-breathe block w-full rounded-xl bg-card text-left"
    >
      <div className="flex items-center justify-between rounded-t-xl border-b border-esc/25 bg-esc-dim/60 px-5 py-2.5">
        <span className="font-mono text-[10.5px] font-medium uppercase tracking-[0.2em] text-esc">
          Escalation — coach review
        </span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-esc/70">
          {entry.clientId}
        </span>
      </div>

      <div className="px-5 py-4">
        <div className="mb-2.5 flex items-baseline gap-2.5">
          <span className="font-display text-[16px] font-semibold text-t1">{client.name}</span>
          <span className="text-[11.5px] text-t3">{client.goal}</span>
        </div>

        <p className="mb-2 font-display text-[15px] font-medium leading-snug text-t1">
          “{entry.text}”
        </p>
        <p className="mb-4 text-[12.5px] leading-relaxed text-esc/90">{entry.triage.reason}</p>

        {entry.triage.action && (
          <div className="mb-3 flex gap-2.5 rounded-lg bg-esc-dim/70 px-3.5 py-3">
            <ArrowRight size={13} className="mt-0.5 shrink-0 text-esc" />
            <div>
              <span className="mb-0.5 block font-mono text-[9.5px] uppercase tracking-[0.2em] text-esc/70">
                Recommended action
              </span>
              <p className="text-[12.5px] font-medium leading-relaxed text-t1">
                {entry.triage.action}
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-2 border-t border-line pt-3">
          <MessageSquare size={12} className="mt-0.5 shrink-0 text-t3" />
          <p className="text-[12px] leading-relaxed text-t3">{entry.checkin}</p>
        </div>
      </div>
    </button>
  );
}
