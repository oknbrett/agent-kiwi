// ─── Types ────────────────────────────────────────────────────────────────────

export type Decision = 'escalate' | 'monitor' | 'none' | 'quiet';

export interface Client {
  id: string;
  name: string;
  initials: string;
  goal: string;
  notes: string;
  avatarHue: number; // OKLCH hue for avatar background
}

export interface MemoryEntry {
  id: string;
  type: 'profile' | 'observation' | 'escalation' | 'waiting';
  body: string;
  date: string;
  confidence?: number; // 0–1, observations only
}

export interface TriageResult {
  decision: Decision;
  reason: string;
  action?: string; // recommended_action — only on escalate
}

export interface ObsEntry {
  clientId: string;
  text: string;
  triage: TriageResult;
  checkin: string;
}

export interface DigestEntry {
  clientId: string;
  decision: Decision;
  text: string;
}

export interface DayData {
  date: string;
  label: string;
  shortLabel: string;
  entries: ObsEntry[];
  digest: DigestEntry[];
  worstDecision: Decision;
}

// ─── Clients ──────────────────────────────────────────────────────────────────

export const CLIENTS: Client[] = [
  {
    id: 'maya',
    name: 'Maya',
    initials: 'MA',
    goal: 'Marathon in 10 weeks',
    notes: 'Experienced runner, high adherence. The happy path.',
    avatarHue: 220,
  },
  {
    id: 'tom',
    name: 'Tom',
    initials: 'TO',
    goal: 'Lose 8kg in 12 weeks',
    notes: 'Trains before work. Tends to downplay problems and goes quiet when work is busy.',
    avatarHue: 285,
  },
  {
    id: 'sofia',
    name: 'Sofia',
    initials: 'SO',
    goal: 'Return to running post-ACL',
    notes: 'Left ACL reconstruction last year. Physio-cleared for light loading only.',
    avatarHue: 40,
  },
  {
    id: 'liam',
    name: 'Liam',
    initials: 'LI',
    goal: 'Back into a regular routine',
    notes: 'Re-starting after a long break. History of ghosting check-ins.',
    avatarHue: 180,
  },
];

// ─── Memory (end-of-week state per client) ────────────────────────────────────

export const MEMORIES: Record<string, MemoryEntry[]> = {
  maya: [
    {
      id: 'm-1',
      type: 'profile',
      body: 'Marathon race in 10 weeks; experienced, high-discipline runner',
      date: '2026-06-01',
    },
    {
      id: 'm-2',
      type: 'observation',
      body: 'Consistent high-adherence; reliably hits target paces',
      date: '2026-06-01',
      confidence: 0.95,
    },
    {
      id: 'm-3',
      type: 'observation',
      body: 'Heavy DOMS after interval sessions; absorbs well by next day',
      date: '2026-06-04',
      confidence: 0.8,
    },
  ],
  tom: [
    {
      id: 't-1',
      type: 'observation',
      body: 'Downplays aches; says "I\'m fine" even when something is off',
      date: '2026-05-15',
      confidence: 0.9,
    },
    {
      id: 't-2',
      type: 'observation',
      body: 'Goes quiet and skips sessions when work gets busy',
      date: '2026-06-02',
      confidence: 0.75,
    },
    {
      id: 't-3',
      type: 'observation',
      body: 'Morning sessions are most reliable attendance window',
      date: '2026-06-01',
      confidence: 0.7,
    },
  ],
  sofia: [
    {
      id: 's-1',
      type: 'profile',
      body: 'Left ACL reconstruction; physio-cleared for light loading only',
      date: '2026-05-01',
    },
    {
      id: 's-2',
      type: 'observation',
      body: 'Mild stiffness after exercise; settles within an hour of finishing',
      date: '2026-06-01',
      confidence: 0.65,
    },
    {
      id: 's-3',
      type: 'observation',
      body: 'Stair-loading aggravates knee; ache noted on two separate days',
      date: '2026-06-03',
      confidence: 0.82,
    },
    {
      id: 's-4',
      type: 'observation',
      body: 'Clicking sound during loaded lunges (no pain at time of report)',
      date: '2026-06-04',
      confidence: 0.55,
    },
    {
      id: 's-5',
      type: 'escalation',
      body: 'ESCALATE: Sharp post-surgical knee pain worsening on stairs — flagged Fri Jun 5',
      date: '2026-06-05',
    },
  ],
  liam: [
    {
      id: 'l-1',
      type: 'waiting',
      body: 'No reply to the previous two check-ins before this week',
      date: '2026-05-28',
    },
    {
      id: 'l-2',
      type: 'waiting',
      body: 'No activity logged across the full week of Jun 1–5',
      date: '2026-06-05',
    },
  ],
};

// ─── Week data — realistic simulated agent outputs ────────────────────────────

export const DAYS: DayData[] = [
  {
    date: '2026-06-01',
    label: 'Monday, June 1',
    shortLabel: 'Mon',
    worstDecision: 'monitor',
    entries: [
      {
        clientId: 'maya',
        text: "Felt great on today's tempo run, hit all my paces.",
        triage: {
          decision: 'none',
          reason: 'Routine positive report; pacing and effort both appropriate.',
        },
        checkin:
          "Solid tempo session — pacing is right on target with 10 weeks to race day. Easy effort tomorrow and prioritise sleep tonight.",
      },
      {
        clientId: 'tom',
        text: 'Got the morning session in before work, felt good.',
        triage: {
          decision: 'none',
          reason: 'Attendance and effort both positive; no concerns.',
        },
        checkin:
          "Good start to the week, Tom. Morning sessions are your most reliable window — keep protecting that slot.",
      },
      {
        clientId: 'sofia',
        text: 'Did my rehab exercises, knee a little stiff but nothing bad.',
        triage: {
          decision: 'monitor',
          reason:
            'Post-exercise stiffness in a post-surgical knee is expected at this recovery stage, but warrants ongoing tracking.',
        },
        checkin:
          "Good consistency with the rehab today, Sofia. Mild stiffness at this stage is expected — note whether it settles within an hour of finishing. That's the key signal to watch.",
      },
    ],
    digest: [
      {
        clientId: 'sofia',
        decision: 'monitor',
        text: 'Mild post-rehab stiffness — expected for ACL recovery stage; monitoring pattern.',
      },
      { clientId: 'maya', decision: 'none', text: 'Tempo paces hit. On track for race week.' },
      { clientId: 'tom', decision: 'none', text: 'Morning session completed. Solid start.' },
      { clientId: 'liam', decision: 'quiet', text: 'No check-in logged.' },
    ],
  },
  {
    date: '2026-06-02',
    label: 'Tuesday, June 2',
    shortLabel: 'Tue',
    worstDecision: 'monitor',
    entries: [
      {
        clientId: 'maya',
        text: 'Easy recovery run, legs feel fresh.',
        triage: {
          decision: 'none',
          reason: "Recovery tracking well after Monday's tempo session.",
        },
        checkin:
          "Fresh legs after Monday's effort — absorbing well. Perfect day to stay easy.",
      },
      {
        clientId: 'tom',
        text: 'Had to skip today, work was completely mad.',
        triage: {
          decision: 'monitor',
          reason:
            'Missed session attributed to work overload — consistent with known pattern of going quiet when busy.',
        },
        checkin:
          "Noted, Tom. Work happens. Worth flagging that last time things got this busy you went quiet for a week — so I'm keeping an eye. What does tomorrow morning look like?",
      },
      {
        clientId: 'sofia',
        text: 'Knee felt stable through the whole session today.',
        triage: {
          decision: 'none',
          reason:
            'Stability improvement vs Monday stiffness — positive progress signal.',
        },
        checkin:
          "Stable through the full session — a step forward from Monday's stiffness. Good sign for your rehab progression.",
      },
    ],
    digest: [
      {
        clientId: 'tom',
        decision: 'monitor',
        text: "Missed session — work cited. Matches prior skip pattern; monitoring follow-through tomorrow.",
      },
      { clientId: 'maya', decision: 'none', text: 'Recovery on track. Legs fresh.' },
      {
        clientId: 'sofia',
        decision: 'none',
        text: 'Improved stability vs Monday. No stiffness reported.',
      },
      { clientId: 'liam', decision: 'quiet', text: 'No check-in logged.' },
    ],
  },
  {
    date: '2026-06-03',
    label: 'Wednesday, June 3',
    shortLabel: 'Wed',
    worstDecision: 'monitor',
    entries: [
      {
        clientId: 'maya',
        text: 'Long intervals this morning, really tough but I got through them.',
        triage: {
          decision: 'none',
          reason: 'Hard interval session completed as planned — expected difficulty, no concern.',
        },
        checkin:
          "Intervals in the bank. Tough is exactly the point at this stage. Legs will be heavy tomorrow — that's expected, not a problem.",
      },
      {
        clientId: 'sofia',
        text: 'Bit of an ache after going up and down the stairs at work.',
        triage: {
          decision: 'monitor',
          reason:
            'Stair-loading ache in a post-ACL knee outside of formal rehab is a pattern worth tracking.',
        },
        checkin:
          "The stair ache is useful data, Sofia — it tells us how the knee responds to incidental loading. Does it ease off when you sit? Let me know.",
      },
    ],
    digest: [
      {
        clientId: 'sofia',
        decision: 'monitor',
        text: 'Stair-loading ache noted outside rehab. Second observation this week; monitoring.',
      },
      {
        clientId: 'maya',
        decision: 'none',
        text: 'Key interval session completed. Expect DOMS Thursday.',
      },
      {
        clientId: 'tom',
        decision: 'quiet',
        text: 'No check-in — second day after Tuesday skip.',
      },
      { clientId: 'liam', decision: 'quiet', text: 'No check-in logged.' },
    ],
  },
  {
    date: '2026-06-04',
    label: 'Thursday, June 4',
    shortLabel: 'Thu',
    worstDecision: 'monitor',
    entries: [
      {
        clientId: 'maya',
        text: "Legs are wrecked after yesterday's intervals, can barely walk.",
        triage: {
          decision: 'none',
          reason:
            'Post-interval DOMS in an experienced marathon runner after a hard session — expected and appropriate.',
        },
        checkin:
          "That's textbook post-interval DOMS, Maya — not an injury. Light movement, good hydration, and you'll be fine by Friday. You're not broken.",
      },
      {
        clientId: 'tom',
        text: 'Back at it this morning, decent session.',
        triage: {
          decision: 'none',
          reason: 'Returned after Tuesday skip; re-engagement positive.',
        },
        checkin:
          "Good to see you back, Tom. You don't need to make up for Tuesday — just keep the forward momentum.",
      },
      {
        clientId: 'sofia',
        text: 'Noticed my knee clicking a little during lunges.',
        triage: {
          decision: 'monitor',
          reason:
            'Clicking in a post-ACL knee during loaded movement warrants tracking; no pain reported yet.',
        },
        checkin:
          "Clicking in a post-surgical knee during lunges is worth logging, Sofia. Was there any pain with it, or just the sensation? Keep note for tomorrow.",
      },
    ],
    digest: [
      {
        clientId: 'sofia',
        decision: 'monitor',
        text: 'Knee clicking during lunges — no pain. Third concern this week; watching closely.',
      },
      {
        clientId: 'maya',
        decision: 'none',
        text: 'DOMS as expected after Wednesday intervals. Not a concern.',
      },
      { clientId: 'tom', decision: 'none', text: 'Returned after Tuesday. Back on track.' },
      { clientId: 'liam', decision: 'quiet', text: 'No check-in logged.' },
    ],
  },
  {
    date: '2026-06-05',
    label: 'Friday, June 5',
    shortLabel: 'Fri',
    worstDecision: 'escalate',
    entries: [
      {
        clientId: 'sofia',
        text: "Sharp pain in my surgical knee today, and it's worse going downstairs.",
        triage: {
          decision: 'escalate',
          reason:
            'Sharp pain in a post-surgical knee aggravated by stair descent — in a client cleared for light loading only — requires immediate coach review.',
          action:
            'Contact Sofia today. Advise no loading until reviewed. Assess whether a physio appointment is needed before her next session.',
        },
        checkin:
          "Sofia, I've flagged this for your coach to review straight away. Sharp pain in a post-surgical knee — especially worse going downstairs — is not something to push through. Please wait to hear from your coach before your next session.",
      },
      {
        clientId: 'maya',
        text: 'Starting to taper, feeling strong and ready.',
        triage: {
          decision: 'none',
          reason: 'Positive taper start with strong readiness signal 10 weeks from race day.',
        },
        checkin:
          "This is what good taper feels like. Strong and ready at this point means the training has landed. Trust the work.",
      },
      {
        clientId: 'tom',
        text: 'Good week overall, three sessions done.',
        triage: {
          decision: 'none',
          reason: 'Three sessions completed despite Tuesday skip — solid recovery and follow-through.',
        },
        checkin:
          "Three sessions this week — solid. That's the standard to aim for. Good recovery from Tuesday. Enjoy the weekend.",
      },
    ],
    digest: [
      {
        clientId: 'sofia',
        decision: 'escalate',
        text: 'URGENT: Sharp pain in surgical knee, worse on stairs. Post-ACL context; physio-only clearance. Contact today — pause sessions until reviewed.',
      },
      { clientId: 'maya', decision: 'none', text: 'Taper started. Feeling strong. On track.' },
      { clientId: 'tom', decision: 'none', text: '3 of 5 sessions. Solid week despite Tuesday.' },
      { clientId: 'liam', decision: 'quiet', text: 'No activity logged all week.' },
    ],
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function getDecisionForClientOnDay(clientId: string, day: DayData): Decision {
  const entry = day.entries.find((e) => e.clientId === clientId);
  if (entry) return entry.triage.decision;
  // If no entry, check digest for quiet signal
  const digestEntry = day.digest.find((d) => d.clientId === clientId);
  return digestEntry?.decision ?? 'quiet';
}

export function getClientById(id: string): Client {
  return CLIENTS.find((c) => c.id === id)!;
}

export function getDayByDate(date: string): DayData {
  return DAYS.find((d) => d.date === date)!;
}
