import type { ReactNode } from 'react';

/** Line icons for the household sections (24x24 grid, drawn with currentColor). */
interface IconProps {
  size?: number;
}

function Svg({ size = 24, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** Costs: a receipt with a zigzag edge */
export function CostsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z" />
      <path d="M9 8h6M9 12h6M9 16h3" />
    </Svg>
  );
}

/** Tasks: a clipboard with a check mark */
export function TasksIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4V3h6v1" />
      <path d="M9 13l2 2 4-4.5" />
    </Svg>
  );
}

/** Tools: a toolbox with a handle and latch */
export function ToolsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 8V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V8" />
      <rect x="3" y="8" width="18" height="12" rx="2" />
      <path d="M3 13h7M14 13h7" />
      <rect x="10" y="11.5" width="4" height="3" rx="0.5" />
    </Svg>
  );
}

/** Task actions menu: a list with a "more" column of dots */
export function TaskActionsIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 6h10M4 12h10M4 18h7" />
      <circle cx="19" cy="6" r="1" fill="currentColor" />
      <circle cx="19" cy="12" r="1" fill="currentColor" />
      <circle cx="19" cy="18" r="1" fill="currentColor" />
    </Svg>
  );
}

/** Notifications: a bell */
export function BellIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" />
      <path d="M10 20.5a2 2 0 0 0 4 0" />
    </Svg>
  );
}

/** Account: a person in a circle */
export function AccountIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="10" r="3" />
      <path d="M6.5 18.5a6.5 6.5 0 0 1 11 0" />
    </Svg>
  );
}

/** Recurring: two arrows going around */
export function RepeatIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 11a7 7 0 0 1 12.5-4.3L19 9" />
      <path d="M19 4v5h-5" />
      <path d="M20 13a7 7 0 0 1-12.5 4.3L5 15" />
      <path d="M5 20v-5h5" />
    </Svg>
  );
}

/** Trash can (delete buttons) */
export function TrashIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3" />
    </Svg>
  );
}
