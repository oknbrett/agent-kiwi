import { DayData } from '../data';
import { DECISION } from '../decision';

interface Props {
  days: DayData[];
  selectedDate: string;
  onSelect: (date: string) => void;
}

export default function WeekTimeline({ days, selectedDate, onSelect }: Props) {
  return (
    <nav
      aria-label="Week"
      className="flex shrink-0 items-stretch gap-0.5 border-b border-line bg-panel px-6 pt-3"
    >
      {days.map((day) => {
        const isSelected = day.date === selectedDate;
        const d = DECISION[day.worstDecision];
        const dayNum = parseInt(day.date.split('-')[2], 10);

        return (
          <button
            key={day.date}
            onClick={() => onSelect(day.date)}
            aria-current={isSelected ? 'date' : undefined}
            className={`relative flex flex-col items-center gap-0.5 rounded-t-md px-5 pb-2.5 pt-1.5 transition-colors duration-200 ${
              isSelected ? 'bg-card' : 'hover:bg-card/50'
            }`}
          >
            <span className="flex items-baseline gap-1.5">
              <span
                className={`font-display text-[13px] font-semibold transition-colors duration-200 ${
                  isSelected ? 'text-t1' : 'text-t3'
                }`}
              >
                {day.shortLabel}
              </span>
              <span className="font-mono text-[10px] tabular-nums text-t3">{dayNum}</span>
            </span>
            <d.Icon size={11} className={`${d.color} ${isSelected ? '' : 'opacity-60'}`} />
            {/* Selected-day underline in the brand green */}
            <span
              className={`absolute inset-x-3 bottom-0 h-[2px] rounded-full transition-opacity duration-200 ${
                isSelected ? 'bg-kiwi opacity-100' : 'opacity-0'
              }`}
            />
          </button>
        );
      })}
    </nav>
  );
}
