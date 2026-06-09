// Shared decision → visual vocabulary. One source of truth so every panel
// renders a tier identically (icon, color, label).
import { ComponentType } from 'react';
import { Decision } from './data';
import { AlertTriangle, CheckCircle, Eye, MoonStar } from './components/Icons';

export const DECISION: Record<
  Decision,
  {
    label: string;
    color: string; // text/icon
    dim: string; // background tint
    Icon: ComponentType<{ size?: number; className?: string }>;
  }
> = {
  escalate: { label: 'Escalate', color: 'text-esc', dim: 'bg-esc-dim', Icon: AlertTriangle },
  monitor: { label: 'Monitor', color: 'text-mon', dim: 'bg-mon-dim', Icon: Eye },
  none: { label: 'Clear', color: 'text-ok', dim: 'bg-ok-dim', Icon: CheckCircle },
  quiet: { label: 'Quiet', color: 'text-qt', dim: 'bg-raise', Icon: MoonStar },
};
