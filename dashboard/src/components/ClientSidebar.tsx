import { Client, DayData, getDecisionForClientOnDay } from '../data';
import { DECISION } from '../decision';

interface Props {
  clients: Client[];
  selectedClientId: string;
  selectedDay: DayData;
  onSelect: (id: string) => void;
}

export default function ClientSidebar({ clients, selectedClientId, selectedDay, onSelect }: Props) {
  return (
    <aside className="flex w-[224px] shrink-0 flex-col border-r border-line bg-panel">
      <div className="px-5 pb-2 pt-5">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-t3">Clients</h2>
      </div>

      <ul className="flex flex-col px-2.5">
        {clients.map((client) => {
          const decision = getDecisionForClientOnDay(client.id, selectedDay);
          const d = DECISION[decision];
          const isSelected = client.id === selectedClientId;
          const isEscalated = decision === 'escalate';

          return (
            <li key={client.id}>
              <button
                onClick={() => onSelect(client.id)}
                aria-pressed={isSelected}
                className={`group flex w-full items-center gap-3 rounded-lg px-2.5 py-2.5 transition-colors duration-200 ${
                  isSelected ? 'bg-raise' : 'hover:bg-card'
                }`}
              >
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-display text-[11px] font-semibold ${
                    isEscalated ? 'bg-esc-dim text-esc' : 'bg-raise text-t2'
                  } ${isSelected && !isEscalated ? 'text-t1' : ''}`}
                  style={
                    !isEscalated
                      ? { backgroundColor: `oklch(26% 0.05 ${client.avatarHue})` }
                      : undefined
                  }
                >
                  {client.name.slice(0, 2).toUpperCase()}
                </span>

                <span className="flex min-w-0 flex-1 flex-col">
                  <span
                    className={`truncate font-display text-[13px] font-medium leading-tight ${
                      isSelected ? 'text-t1' : 'text-t2 group-hover:text-t1'
                    } transition-colors duration-200`}
                  >
                    {client.name}
                  </span>
                  <span className="mt-0.5 truncate text-[11px] leading-tight text-t3">
                    {client.goal}
                  </span>
                </span>

                <d.Icon size={13} className={`${d.color} shrink-0 opacity-90`} />
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto border-t border-line px-5 py-4">
        <h3 className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.22em] text-t3">
          Triage tiers
        </h3>
        <ul className="flex flex-col gap-1.5">
          {(Object.keys(DECISION) as (keyof typeof DECISION)[]).map((key) => {
            const d = DECISION[key];
            return (
              <li key={key} className="flex items-center gap-2">
                <d.Icon size={12} className={d.color} />
                <span className="text-[11px] text-t3">{d.label}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
